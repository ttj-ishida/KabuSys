# CHANGELOG

すべての注目すべき変更を記載します。本プロジェクトは Keep a Changelog の慣例に従っています。  
リリースはセマンティックバージョニングに基づきます。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース。KabuSys: 日本株自動売買／データ基盤／リサーチ用ユーティリティ群を提供。
- パッケージ初期エントリポイント
  - src/kabusys/__init__.py: バージョン定義および公開モジュール一覧（data, strategy, execution, monitoring）。
- 設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルート（.git または pyproject.toml）を基準に自動検出して .env / .env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export 形式やシングル/ダブルクォート、インラインコメント等を考慮した堅牢な .env パーサ実装。
    - override / protected logic による OS 環境変数保護機能。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境（development/paper_trading/live）やログレベル検証などをプロパティで取得可能。環境値検証で不正値は ValueError を発生。
- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄別に集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を計算、ai_scores テーブルへ書き込み。
    - チャンクバッチング（最大20銘柄/回）、1銘柄あたりの記事数・文字数制限、JSON Mode の期待レスポンス検証、レスポンス復元（前後の雑多なテキストが混入した場合の {} 抽出）などの堅牢化。
    - リトライ（429/ネットワーク/タイムアウト/5xx）で指数バックオフ。非再試行エラーはスキップして継続、API失敗時は例外を投げずフェイルセーフにフォールバック。
    - スコアは ±1.0 にクリップ。部分失敗を避けるため、取得済みコードのみ DELETE→INSERT による置換を行う（冪等性・部分失敗保護）。
    - 単体テスト用に内部 API 呼び出し関数を差し替え可能（unittest.mock.patch 対応）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - prices_daily を target_date 未満のデータのみ参照してルックアヘッドバイアスを防止。
    - マクロニュース抽出（キーワードフィルタ）→ OpenAI 評価（JSON mode）→ 合成 → DB 書き込みのフローを実装。API失敗時は macro_sentiment=0.0 として継続。
- データ基盤（Data）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。探索範囲上限 (_MAX_SEARCH_DAYS) を設け無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック有り）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインのためのユーティリティと ETLResult データクラスを実装（取得・保存件数、品質問題・エラー一覧等を格納）。
    - 差分取得、バックフィル、品質チェックの設計方針を反映。jquants_client を用いた idempotent な保存を想定。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート。
- Research（リサーチ用解析）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value（PER, ROE）など複数のファクター算出関数を実装（prices_daily, raw_financials を参照）。
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - ボラティリティ: 20日 ATR、ATR比率、20日平均売買代金、出来高比率。
    - バリュー: target_date 以前の最新財務を参照して PER/ROE を計算。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力バリデーション付き）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）、ランク関数（同順位は平均ランクを採用し丸めで ties を安定検出）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を外部依存なしで実装。
  - src/kabusys/research/__init__.py: 便利関数群を再エクスポート。
- 汎用/実装設計上の注意点
  - DuckDB を一次データ層として利用する設計。SQL + Python の組合せで処理を完結。
  - 外部ライブラリ（pandas 等）に依存しない実装を意図。
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today() / date.today() を安易に使わない方針を徹底（score_news/score_regime 等で target_date 引数を必須）。
  - OpenAI 呼び出しは JSON モードを前提に厳密な JSON を期待、かつ実運用でのノイズを想定して復元ロジックを実装。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- フェイルセーフと冪等性を各所で強化:
  - OpenAI API の失敗時に例外を上位へそのまま投げず、明示的にフォールバック値（macro_sentiment=0.0 等）を採る実装。
  - DB 書き込みでの BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ログの追加により、部分失敗時の状態保全を強化。
  - DuckDB executemany の特性（空リスト不可）に対するガードを導入。
  - .env パースの頑強化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用。コード内にハードコードしない設計。機密性の高い環境変数は .env.local などでローカルに管理することを想定。

---

注記:
- テスト容易性として、AI モジュール内の API 呼び出しラッパー（_kabusys.ai.*._call_openai_api）は unittest.mock.patch により差し替え可能な形で実装されています。
- 本 CHANGELOG は現行のソースコードから実装方針・機能を推定して作成したものであり、実際のコミット履歴やプロジェクト要求書に基づくものではありません。必要に応じて日付や項目を調整してください。