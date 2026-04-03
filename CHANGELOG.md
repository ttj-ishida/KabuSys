Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

保持ポリシーの説明やセクション構成は Keep a Changelog の形式に従っています。
日付は本日時点（2026-04-03）での初回リリース v0.1.0 を想定しています。必要に応じて日付やバージョンを調整してください。

-------------------------------------------------------------------
CHANGELOG.md
-------------------------------------------------------------------

Keep a Changelog
================
すべての重要な変更点をこのファイルで管理します。  
フォーマットは https://keepachangelog.com/ja/ に準拠します。

変更履歴は以下のセクション順で記載します:
- Unreleased: 次リリースに向けた未リリースの変更
- [x.y.z] - YYYY-MM-DD: 各リリースの変更内容

Unreleased
----------
- （現在なし）

[0.1.0] - 2026-04-03
--------------------
Added
- パッケージの初回公開:
  - kabusys パッケージ（__version__ = 0.1.0）
  - モジュール群を公開: data, research, ai, config, 等。

- 環境設定 / 設定管理:
  - kabusys.config.Settings を導入。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - OS 環境変数を保護する protected キーの概念と override 処理。
    - 必須変数取得用 _require()（未設定時は ValueError）。
    - 各種プロパティ（J-Quants トークン、kabu API 設定、LINE トークン、DB パス、監視ファイルパス、リソース閾値、環境モード、ログレベル判定等）。

- AI（ニュースNLP / レジーム判定）:
  - kabusys.ai.news_nlp.score_news
    - 指定日のニュースウィンドウ（前日15:00 JST〜当日08:30 JST）を計算。
    - raw_news / news_symbols を銘柄ごとに集約し、1銘柄あたり最大記事数／最大文字数でトリム。
    - OpenAI（gpt-4o-mini）へ最大20銘柄のバッチ送信。
    - レスポンス検証（JSON復元/構造チェック/数値チェック）、スコア ±1.0 でクリップ。
    - DuckDB へ部分置換（DELETE→INSERT）することで部分失敗時に既存データを保護。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - APIキー未指定時は ValueError を送出。

  - kabusys.ai.regime_detector.score_regime
    - ETF 1321 の200日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）判定。
    - prices_daily からの ma200_ratio 計算（target_date 未満のみ使用、ルックアヘッド防止）。
    - raw_news からマクロキーワードに一致するタイトルを収集して LLM に投げる（記事がない場合は LLM 呼び出しをスキップし macro_sentiment=0.0）。
    - OpenAI 呼び出しに対するリトライ制御とフェイルセーフ（API失敗時は macro_sentiment=0.0 として継続）。
    - 結果を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Research（ファクター / 特徴量探索）:
  - kabusys.research.factor_research
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio を計算。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計上、prices_daily / raw_financials のみ参照し外部発注 API へはアクセスしない。

  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定日から将来リターン（horizons デフォルト [1,5,21]）を計算。
    - calc_ic: Spearman（ランク相関）で IC を計算（有効レコードが3未満の場合は None）。
    - rank: 同順位は平均ランクで扱うランク変換。
    - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。
    - 依存を最小化し、標準ライブラリと DuckDB のみで実装。

- Data（カレンダー / ETL / パイプライン）:
  - kabusys.data.calendar_management
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日の曜日ベース（平日のみ営業日）フォールバックを一貫して実装。
    - calendar_update_job: J-Quants API から差分取得し market_calendar テーブルへ冪等保存（バックフィル、健全性チェックあり）。

  - kabusys.data.pipeline / etl
    - ETLResult データクラス（取得数・保存数・品質問題・エラー集計）を実装し etl モジュールで再エクスポート。
    - 差分取得・保存・品質チェックのためのインフラを提供（jquants_client / quality モジュールと連携を想定）。
    - エラーは収集して戻し、呼び出し元が対処する設計（Fail-Fast ではない）。

- 互換性・内部ユーティリティ:
  - DuckDB を中心とした SQL 実行を前提に実装（日付ハンドリング、fetch/exists ユーティリティ）。
  - OpenAI クライアント呼び出し部分は各モジュールで独立実装（テスト容易性のためモック可能）。
  - ロギングと詳細な警告メッセージを多数追加。

Changed
- 初回リリースのため該当なし。

Fixed
- API 呼び出し失敗ケースの堅牢化:
  - OpenAI API 呼び出しでの RateLimit / 接続エラー / タイムアウト / 5xx をリトライ（指数バックオフ）し、最終的失敗でもシステムが継続可能なデフォルト（例: macro_sentiment=0.0）を選択する仕様を採用。
  - news_nlp では JSON 解析失敗時にレスポンスから最外の {} を抽出して復元を試みるなど耐性を向上。
- DuckDB executemany の空リストバインド制約を回避する処理を追加（空リストの場合は呼び出しをスキップ）。

Security
- OpenAI API キーは必須（関数内で解決）。未設定時は ValueError を送出して明示的に失敗する。
- .env 読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。

Notes（設計上の重要事項・制限）
- ルックアヘッドバイアス回避:
  - score_news / score_regime など時間依存処理は datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す方式を採用。
  - DB クエリは target_date 未満（排他）や半開区間でウィンドウ指定することで将来データ参照を防止。
- 一部未実装（今後の実装予定）:
  - calc_value での PBR・配当利回りは未実装。
- DB スキーマ前提:
  - このコードは prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などのテーブル存在を前提とする。実行前にスキーマを整備してください。
- 外部依存:
  - OpenAI SDK（chat/completions）、DuckDB、J-Quants クライアントモジュール（kabusys.data.jquants_client）などが必要。

Migration / Usage notes
- 環境変数を設定（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- .env/.env.local をプロジェクトルートに配置すると自動読み込みされる（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化）。
- DuckDB 接続を用意し、各テーブルの有無・スキーマを確認してから各関数（score_news, score_regime, calc_*）を呼び出してください。
- news_nlp / regime_detector の OpenAI 呼び出しはテスト時にモック可能（各モジュール内の _call_openai_api を patch する設計）。

-------------------------------------------------------------------

必要があれば次の点を調整します:
- 追加したい過去の開発履歴やリリース日を反映
- 英語版の CHANGELOG を併記
- 変更点をより細かくモジュール/関数レベルで分割して記載

どのように出力したいか（単体ファイル、リポジトリへの追加、日付変更など）を教えてください。