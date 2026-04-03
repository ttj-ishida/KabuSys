# CHANGELOG

すべての変更はこのファイルに記録されています。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針:
- バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。  
- 日付は本CHANGELOG作成日（2026-04-03）を使用しています（必要に応じて実際のリリース日に差し替えてください）。

## [Unreleased]

## [0.1.0] - 2026-04-03
初期リリース。プロジェクトのコア機能群を実装し公開しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - 初期パッケージ構成を追加（kabusys）。公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ に記載）。
  - バージョン: 0.1.0。

- 設定・環境読み込み（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み順: OS環境 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env のパース実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを実装し、アプリの主要設定値をプロパティ経由で取得可能に。
    - 必須・オプションの環境変数を整理（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY を利用可）。
    - デフォルト値を持つ項目（KABU_API_BASE_URL、データベースパス、PID/KILL ファイルパス、しきい値、ログレベル等）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）およびログレベル検査。

- データプラットフォーム関連（src/kabusys/data）
  - calendar_management.py
    - JPXカレンダー管理・営業日判定ロジックを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得時は曜日ベースのフォールバックを使用。
    - calendar_update_job を実装し J-Quants から差分取得して保存（バックフィル・健全性チェック含む）。
  - pipeline.py / etl.py
    - ETL 基盤と ETLResult データクラスを実装（ETL 実行結果の構造化）。
    - 差分更新、バックフィル、品質チェックを想定した ETL の設計方針を実装。
    - jquants_client と quality モジュールとの連携ポイントを用意（fetch/save 呼び出し箇所）。
  - jquants_client との連携を想定した idempotent 保存設計（ON CONFLICT 相当の扱い）を行うことを想定。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大20銘柄／チャンク）、トークン肥大対策（記事数・文字数制限）、JSON Mode 利用、レスポンスバリデーションを実装。
    - リトライ方針: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ。
    - フェイルセーフ: API失敗やパース失敗時は当該チャンクをスキップして他チャンクへ継続。
    - テスト容易性: _call_openai_api を patch 可能にしてモック注入を想定。
    - calc_news_window 関数により JST ベースのニュースウィンドウを厳密に計算（ルックアヘッドバイアス防止）。
  - regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLMセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装（score_regime）。
    - ma200_ratio の計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API障害時のフォールバック（macro_sentiment=0.0）やリトライロジックを備える。
    - テスト容易性: news_nlp とプライベート関数を共有しない設計（モジュール結合を抑制）。

- リサーチ（ファクター・特徴量探索: src/kabusys/research）
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。
      - calc_value: PER（price/EPS）、ROE を計算（raw_financials の最新値を使用）。PBR・配当利回りは未実装。
    - DuckDB を使って SQL+ウィンドウ関数中心で実装。外部 API にアクセスしない設計。
  - feature_exploration.py
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク変換を実装（丸めによるties対策含む）。
  - research.__init__ で主要関数を再エクスポート。

- 一般設計方針（クロスモジュール）
  - ルックアヘッドバイアス回避: 各モジュールで datetime.today() / date.today() を盲目的に参照せず、明示的な target_date 引数を基本設計に採用。
  - DuckDB を主要なローカル分析 DB として利用。
  - OpenAI との連携は JSON Mode（厳密な JSON 出力）を前提にし、パース失敗時の保護ロジックを備える。
  - API 呼び出しに対する堅牢なリトライ・フォールバック設計（全体の可用性向上を重視）。
  - テストしやすさを考慮し、外部 API 呼び出し箇所（_call_openai_api 等）を差し替え可能に実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の秘密情報は環境変数で管理する設計。
- .env 読み込みは OS 環境変数を保護する機能（protected set）を備え、.env.local で容易に上書き可能。

### Notes / Known limitations
- OpenAI 関連
  - デフォルトモデルは gpt-4o-mini。OpenAI SDK に依存します（適切なバージョンでの動作を想定）。
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要があります。未指定時は ValueError を送出します。
- データベース
  - DuckDB に依存します。DuckDB のバージョン差異（executemany の空リスト扱い等）を考慮した実装を行っていますが、環境によっては注意が必要です。
- 未実装 / 将来実装予定
  - factor_research.calc_value における PBR・配当利回りなどは未実装。
  - jquants_client / quality モジュールの具体的な実装は別途。
- 設定（主な環境変数）
  - 必須想定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（利用機能により）、OPENAI_API_KEY（AI機能を使う場合）
  - 任意・デフォルトあり: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）、PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU/MEMORY/DISK 閾値、KABUSYS_ENV、LOG_LEVEL、LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID
- テスト性
  - OpenAI 呼び出し等はモック置換可能（unittest.mock.patch）にしてあるため、ユニットテストが書きやすい設計です。

---

貢献・バグ報告・機能要望はリポジトリの Issue にて受け付けてください。リリース後のマイナー修正や機能追加は本ファイルの Unreleased セクションに順次記載します。