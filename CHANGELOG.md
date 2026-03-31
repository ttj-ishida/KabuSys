# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Removed, Security 等）に分類しています。
- 日付は本CHANGELOG作成時点（2026-03-31）をリリース日として記載しています。

## [Unreleased]
- 将来の変更・改良点（ここには未反映）

---

## [0.1.0] - 2026-03-31

### Added
- パッケージ基盤
  - パッケージエントリーポイントを導入（src/kabusys/__init__.py）。バージョン情報 __version__ = 0.1.0、および公開モジュール一覧 (__all__ = ["data", "strategy", "execution", "monitoring"] ) を定義。
- 設定 / 環境変数管理
  - 環境変数と .env ファイルを管理する設定モジュールを追加（src/kabusys/config.py）。
    - .env と .env.local の自動読み込みを実装（プロジェクトルートの検出は .git / pyproject.toml ベース）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - .env パースの堅牢化（export プレフィックス対応、クォート内エスケープ処理、インラインコメント処理）。
    - OS 環境変数保護（既存の環境変数を保護する protected キーの導入）。
    - 必須環境変数取得用 _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル検証）。
- AI（ニュースNLP・レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - バッチサイズ、記事数・文字数制限、タイムウィンドウ（JST 基準 → UTC 変換）を定義。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - レスポンス検証（JSON 抽出・構造チェック・スコア数値チェック）とスコアの ±1.0 クリップ。
    - スコア結果を ai_scores テーブルへ冪等的に書き込むロジック（DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - calc_news_window(target_date) ユーティリティを提供（ターゲット日の前日 15:00 JST 〜 当日 08:30 JST を対象）。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースLLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - OpenAI（gpt-4o-mini, JSON mode）呼び出し、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）、レスポンスパース保護を実装。
    - レジームスコアの閾値、スケーリング、クリッピング定義。market_regime テーブルへの冪等書き込みを実施。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
  - AI モジュールエクスポート（src/kabusys/ai/__init__.py）で score_news を公開。

- リサーチ（ファクター・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高比率・平均売買代金）、Value（PER, ROE）等の定量ファクターを DuckDB SQL で実装。
    - データ不足時の None 戻し、結果を (date, code) ベースの dict リストで返す設計。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関、無効レコード処理）。
    - ランク変換（rank: 同順位は平均ランク、丸め処理あり）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - research パッケージの __init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から）。

- データプラットフォーム（calendar / ETL / pipeline）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存）。
    - 営業日判定・前後営業日探索・期間内営業日一覧取得・SQ 日判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DBが未取得の際の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETL の結果を表す ETLResult データクラスを実装（取得/保存件数、品質問題、エラーリストなど）。
    - 差分取得、バックフィル、品質チェックの設計方針を反映したユーティリティを実装。
    - etl.py に ETLResult の再エクスポートを追加。
  - データモジュールのユーティリティ（テーブル存在チェックや最大日付取得など）を実装。

- DB / クライアント関連
  - DuckDB を主要な分析 DB として利用する設計を反映（関数の引数に DuckDB 接続を要求）。
  - jquants_client との連携ポイントを準備（calendar_update_job などで利用）。

- ロギング / エラーハンドリング
  - 各モジュールで詳細なログを追加（info/debug/warning/exception）。
  - OpenAI や I/O エラー時にフェイルセーフな挙動（例: スコアを 0 にフォールバック、処理のスキップ、巻き戻し/ROLLBACK の試行）を実装。

### Changed
- 初版（0.1.0）として多数のサブモジュールを新規追加。今後のリリースで API 安定化やリファクタリングを予定。

### Fixed
- N/A（初期リリース: 実装段階での既知バグ修正履歴なし）

### Security
- 環境変数の取り扱いに注意:
  - 必須トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は Settings で必須チェックを行い、不足時は ValueError を送出。
  - .env 自動ロード時に既存 OS 環境変数を保護する仕組みを導入。

---

注記:
- この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやプロジェクト方針に合わせて日付・項目を調整してください。