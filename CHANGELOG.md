# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを使用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を公開します。以下はコードベースから推測される主要機能・設計方針・注意点のまとめです。

### 追加 (Added)
- パッケージ公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージのエクスポート: data, strategy, execution, monitoring

- 環境設定管理モジュール (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート/.git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント等を考慮した堅牢な実装。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - OPENAI 用の利用（環境変数名は OPENAI_API_KEY を想定）
    - LINE 関連: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）
    - データベースパスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db
    - 監視用ファイルパスや閾値（PID/KILL フラグ、CPU/MEM/DISK閾値）をプロパティで提供
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）および is_live/is_paper/is_dev ヘルパー

- AI 関連モジュール (kabusys.ai)
  - ニュースセンチメント分析: score_news (kabusys.ai.news_nlp)
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DB 内は UTC として比較）
    - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数・文字数でトリム
    - OpenAI gpt-4o-mini（JSON Mode）へバッチ送信（デフォルトバッチサイズ=20）
    - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ
    - レスポンスを厳密にバリデーションしスコアを ±1.0 にクリップ
    - 成功した銘柄のみ ai_scores テーブルに置換的（DELETE → INSERT）に書き込み（冪等性・部分失敗保護）
    - API キーは引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照
    - フェイルセーフ: API 失敗時は該当チャンクをスキップし処理継続

  - 市場レジーム判定: score_regime (kabusys.ai.regime_detector)
    - 指数ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成
    - LLM モデル: gpt-4o-mini（JSON Mode）、レスポンスは {"macro_sentiment": 0.0} 形式を期待
    - マクロニュースはタイトルベースでキーワードフィルタ（複数の日本語・英語キーワード）
    - API 呼び出しはリトライロジック・フェイルセーフを備え、最終的に macro_sentiment=0.0 にフォールバック
    - 得られたスコアを -1..1 にクリップして regime_label を決定（bull/neutral/bear）
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみ参照・date.today() を参照しない設計

  - AI モジュール一般
    - OpenAI 呼び出し用に _call_openai_api を各モジュール内に実装（モジュール間で private 関数を共有しない）
    - テスト用に各モジュールの API 呼出し関数を patch 置換しやすい設計

- データプラットフォーム (kabusys.data)
  - カレンダー管理: calendar_management
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 未取得時は曜日ベース（土日休）でフォールバック
    - 最大探索日数や健全性チェック、バックフィルロジックを実装
    - 夜間バッチ job: calendar_update_job を提供（J-Quants API から差分取得し保存）
    - jquants_client（jq）経由で API 呼び出し・保存処理を委譲

  - ETL パイプライン: pipeline, etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）
    - 差分更新 / バックフィル / 品質チェック（quality モジュール）を想定した設計
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を有する
    - 品質チェックは致命的エラーがあっても全件収集する「Fail-Safe」方針
    - jquants_client を通じた idempotent な保存（ON CONFLICT DO UPDATE）を想定

- リサーチ機能 (kabusys.research)
  - ファクター計算: calc_momentum, calc_value, calc_volatility
    - momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）
    - volatility: 20日 ATR、ATR/株価、20日平均売買代金、出来高比率等を計算
    - value: raw_financials から EPS/ROE を参照して PER/ROE を計算
    - すべて DuckDB 上の prices_daily / raw_financials のみを参照し外部 API にアクセスしない設計
    - 結果は (date, code) をキーとする dict のリストで返す
  - 特徴量探索: calc_forward_returns, calc_ic, rank, factor_summary
    - forward returns: 任意ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算（horizons の検証あり）
    - IC (Spearman ρ) 計算: factor と将来リターンのランク相関を算出（有効レコード <3 の場合 None を返す）
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出漏れを防止）
    - factor_summary: count/mean/std/min/max/median を計算
    - 外部依存（pandas 等）を持たない純標準ライブラリ実装

### 設計上の注意点 / 挙動
- ルックアヘッドバイアス回避のため、全 AI / リサーチ / ETL 関数は内部で date.today()/datetime.today() を参照せず、呼び出し側から target_date を明示的に渡す設計。
- OpenAI API は gpt-4o-mini・JSON Mode を利用する前提。レスポンスの整形やパース失敗時は安全側にフォールバックし、例外を上位に伝播させず処理を継続する箇所が多い（フェイルセーフ設計）。
- DuckDB 0.10 系の互換性（executemany の空リスト不可やリストバインドの挙動）に配慮した実装。
- DB 書き込みは可能な限り冪等性（DELETE→INSERT / ON CONFLICT）を担保するように実装。
- テスト容易性: OpenAI 呼び出し関数や環境自動読み込みは外部から無効化・差し替え可能な設計（patch / 環境変数フラグ）。

### 既知の制約 / 未実装項目
- 現時点でのバリュー関連では PBR や配当利回りは未実装（calc_value の注記あり）。
- news_nlp / regime_detector は OpenAI へ依存するため、API キーとネットワークが必須。
- strategy, execution, monitoring の具体的な実装は公開インターフェースで示されているが、本リリースでは主にデータ／研究／AI 支援系のユーティリティが中心。

### セキュリティ
- 機密情報（API キー等）は環境変数から取得する設計。.env を使用する場合でも OS 環境変数を保護するための protected ロジックを実装。

---

今後のリリースでは、strategy / execution（実際の注文ロジック・kabuステーション連携）や監視・運用自動化機能の拡充、より多様なファクター・バックテスト機能の追加、さらなる堅牢化（例: トランザクション監査・リトライの詳細チューニング）を予定してください。