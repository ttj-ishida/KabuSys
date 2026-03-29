# CHANGELOG

すべての変更は "Keep a Changelog" の形式に従い、セマンティックバージョニングに基づいて記載しています。  

## [0.1.0] - 初回リリース (推定)
リリース日: 不明（コードベースから推測）

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py、__version__ = 0.1.0）。
  - パッケージレベルで主要サブパッケージをエクスポート: data, research, ai など。

- 環境設定・ロード (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - OS 環境変数を保護する protected 機能（.env.local の上書き時にも保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの改善:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメント処理（クォートなし値の '#' をインラインコメント判定する場合の挙動制御）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DBパス等の設定プロパティを定義。
    - env, log_level 等の値検証（許容値セットで不正値は ValueError）。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news / news_symbols を元に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
  - JST 基準のニュース収集ウィンドウ計算を実装（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
  - 1銘柄あたりの記事数・文字数上限（トリム）でトークン肥大化を回避。
  - バッチ送信（最大 20 銘柄/回）と冪等的な DB 書き込み（DELETE → INSERT）。
  - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API失敗時は該当チャンクをスキップして続行。
  - レスポンスの堅牢なバリデーション:
    - JSON mode（厳密 JSON）を利用しつつ、前後に余計なテキストが混ざるケースに対する復元ロジックを実装。
    - 結果の型チェック、未知コードの無視、スコアを ±1.0 にクリップ。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

- 市場レジーム判定（AI + テクニカル） (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を追加。
  - News NLP からのウィンドウ計算関数を利用して記事を抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
  - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - リトライ・バックオフ、5xx の扱い、JSON パース失敗時のフォールバックなどの堅牢性を実装。
  - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う公開 API: score_regime(conn, target_date, api_key=None)。

- データ基盤（Data） (src/kabusys/data/...)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定と補助関数群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録データを優先し、未登録日は曜日ベースのフォールバック（週末除外）で一貫性を保つ実装。
    - カレンダー更新ジョブ（calendar_update_job）: J-Quants から差分取得 → 保存、バックフィル、健全性チェックを実装。
  - ETL / パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを追加（ETL 実行結果・品質問題・エラー情報を保持）。
    - 差分更新・バックフィル戦略、品質チェックの集約、idempotent 保存方針を取り入れた ETL のインターフェース設計。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取込範囲調整等。
  - jquants_client を利用する抽象化（外部クライアント呼び出しを分離）。

- 研究（Research） (src/kabusys/research/...)
  - ファクター計算 (factor_research.py)
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB SQL で計算（データ不足時は None）。
    - Volatility / Liquidity: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS 0/欠損時は None）。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照。返却は dict リスト。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）のリターンを一括取得する SQL 実装。
    - IC 計算 (calc_ic): スピアマンのランク相関（ランク関数含む）でファクターの有効性を評価。
    - rank, factor_summary: ランク化ユーティリティと基本統計量集計を標準ライブラリのみで実装。
  - research パッケージ __init__ で主要関数をまとめて再エクスポート。

### 変更 (Changed)
- 設計上の注意点 / セーフガードの追加（実装段階での設計選択）
  - AI スコアリング系（news_nlp, regime_detector）および研究系の関数は内部で datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス回避のため）。target_date を明示的に受け取る API として実装。
  - DuckDB に対する executemany の空リスト問題（DuckDB 0.10 の制約）を考慮して、空パラメータを事前にチェックしてから実行する防御的実装を追加。

### 修正 (Fixed)
- OpenAI 呼び出し周りの堅牢化
  - JSON パースエラーや API エラーの扱いを明確化し、致命的エラーにならないフォールバック（0.0 やスキップ）を導入。
  - レスポンスに余計なテキストが含まれるケースへの復元ロジックを追加（JSON 抽出）。

### 既知の制限 / 注意点 (Known issues / Notes)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給する必要がある。未設定時は ValueError を送出する。
- news_nlp の出力は現フェーズでは sentiment_score と ai_score が同一（同値）として扱われる。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存する。外部 API エラー時は 0 を返し安全に終了する。
- 一部関数は DuckDB の日付/型の戻り値の扱い（date/str）を考慮した変換ロジックを含む。

---

今後のリリースで期待される改善点（例）
- 追加のファクター（PBR、配当利回り等）の実装。
- AI モデル選択やレスポンスフォーマットの拡張オプション。
- 単体テスト／統合テストの追加（OpenAI 呼び出しのモック化を含む）。
- jquants_client のより詳細なエラーハンドリング・メトリクス収集。

（注）本 CHANGELOG は提供されたソースコードの内容をもとに自動的に推測して作成しています。実際のリリース注記や日付はプロジェクト運用者による確認・更新を推奨します。