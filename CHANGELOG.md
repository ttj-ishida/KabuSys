# Changelog

すべての重要な変更点をここに記載します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

※ ここに記載した内容は、提示されたコードベースから推測してまとめた変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース ("kabusys" v0.1.0)
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージ公開APIとして data, strategy, execution, monitoring をエクスポート。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env/.env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
  - .env パース機能を実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - .env 上書き制御（override）および OS 環境変数保護（protected set）に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数未設定時に ValueError を送出する _require と Settings クラスを提供。
  - J-Quants、kabuステーション、Slack、DB パス、監視設定、システム環境（env / log_level）などのプロパティを実装（デフォルト値・バリデーション含む）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを取得。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）用の calc_news_window 実装。
    - バッチサイズ、記事数・文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - DuckDB への冪等書き込み（取得済みコードのみ DELETE → INSERT）を実装。DuckDB 0.10 の executemany 制約（空リスト不可）に対応。
    - OpenAI 呼び出し箇所はテスト時に差し替え可能（_call_openai_api をモック可能）。
    - score_news(conn, target_date, api_key=None) を実装し、ai_scores テーブルへ書き込む（取得銘柄数を返す）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使いルックアヘッドを防止。
    - マクロニュースは raw_news をキーワードでフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してマクロセンチメントを取得（記事なし時は LLM 呼び出しをスキップ）。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライ・バックオフ、レスポンスパース障害時の安全処理を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - score_regime(conn, target_date, api_key=None) を提供。

  - ai パッケージ初期エクスポート（src/kabusys/ai/__init__.py）
    - score_news を公開 API としてエクスポート。

- 研究・ファクター解析モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev を計算する calc_momentum を実装。データ不足時に None を返す挙動を明示。
    - Volatility/Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算する calc_value を実装（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL 集約実装、戻り値は (date, code) キーを持つ dict のリスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（可変ホライズン、デフォルト [1,5,21]、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、十分なサンプルがない場合は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で ties 対応）。
    - ファクター統計要約 factor_summary（count/mean/std/min/max/median）。
  - research パッケージ初期エクスポート（src/kabusys/research/__init__.py）
    - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を再エクスポート。

- データプラットフォーム関連（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日判定・探索 API を実装。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等に更新するバッチを実装（バックフィル・健全性チェックあり）。
    - DB の未登録日・NULL 値に対するログ出力と一貫したフォールバックロジックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを定義し、取得/保存件数、品質問題、エラー一覧などを保持・辞書化できる to_dict を実装。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計を反映。
    - 内部ユーティリティとしてテーブル存在チェックや最大日付取得などのヘルパを実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の必須チェック機構（_require）により、必須トークン未設定時に早期エラーを発生させる設計を導入。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を提供。

### Design / Implementation notes（設計上の注意点）
- ルックアヘッドバイアス対策: score_news / score_regime などは内部で datetime.today() を参照せず、外部から渡された target_date の過去データのみを参照する。
- フェイルセーフ: LLM/API 失敗時は例外を上位に投げずにフォールバック（スコア 0.0 やスキップ）して処理継続する方針。
- DuckDB 互換性: executemany に空リストを渡せない既知制約に対応した実装（空時は呼ばない等）。
- テスト容易性: OpenAI 呼び出し箇所を差し替え可能にしてユニットテストでのモックを想定。

### Known limitations / TODO
- strategy, execution, monitoring パッケージは __all__ に含まれるが（トップレベルでエクスポートされる）、提示されたコード内にそれらの実装は含まれていないため、今後の実装が必要。
- 一部ファイルの末尾や内部ユーティリティ（pipeline._get_max_date の実装断片など）に未完成箇所が見受けられる。リリース直前に完全な実装・テストを行うことを推奨。

---

（注）この CHANGELOG は与えられたコードベースの内容から推測して作成した初期リリース向けの要約です。実際のリリースノートとして公開する際は、追加の変更点・既知のバグ・テスト状況などを合わせて検証・追記してください。