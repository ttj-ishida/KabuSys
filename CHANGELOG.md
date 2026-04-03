# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  

## [Unreleased]

---

## [0.1.0] - 2026-04-03

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- パッケージ公開:
  - パッケージ名: kabusys、バージョン 0.1.0
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）
- 設定・環境変数管理:
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装（src/kabusys/config.py）。
  - プロジェクトルート探索: .git または pyproject.toml を基準に自動的に探索して .env を読込（CWD に依存しない実装）。
  - .env 解析: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応する堅牢なパーサ実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 環境変数保護（protected set）による上書き制御。  
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 /システム設定のプロパティを公開（必須値の検証を含む）。
  - VALID_ENVS・VALID_LOG_LEVELS による env/log_level のバリデーション。is_live/is_paper/is_dev ユーティリティも実装。
- AI モジュール:
  - ニュースNLP: src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_scores）を生成。
    - チャンク処理（デフォルト 20 銘柄）、1銘柄あたり最大記事数・文字数制限、JSON Mode 応答パースの堅牢化を実装。
    - ネットワーク障害・429・タイムアウト・5xx に対する指数バックオフ・リトライ、レスポンス検証（results 配列、code/score の検証、スコア ±1 にクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
  - 市場レジーム判定: src/kabusys/ai/regime_detector.py
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を算出して market_regime テーブルへ保存。
    - OpenAI 呼び出しのリトライ／フェイルセーフ（API 失敗時は macro_sentiment=0.0 を採用）。
    - DuckDB からのデータ取得はルックアヘッドを防ぐクエリ条件（date < target_date、等）を採用。
    - OpenAI 呼び出しはモジュール独自実装とし、モジュール結合を防止。
- データプラットフォーム:
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar に基づく営業日判定、次/前営業日の検索、期間内営業日リスト取得、SQ日判定の API を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - カレンダー夜間バッチ（calendar_update_job）: J-Quants から差分取得し冪等で保存、バックフィルと健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開し、ETL の取得・保存結果、品質チェック結果、エラーを格納。
    - 差分更新・バックフィル・品質チェックの基本フローを実装。J-Quants クライアント経由で idempotent 保存を行う設計。
    - テーブル存在チェック、最大日付取得などのユーティリティ実装。
  - jquants_client を介したデータ取得と保存を想定した設計（モジュール分離）。
- リサーチ（src/kabusys/research/*）:
  - ファクター計算（factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を使って PER, ROE を計算（最新財務レコードの取得ロジック含む）。
    - DuckDB を用いた SQL ベース実装、欠損・データ不足時の None ハンドリング。
  - 特徴量探索（feature_exploration.py）:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。十分なデータがない場合は None を返す。
    - rank: タイの平均ランク処理を含むランク付けユーティリティ。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
- その他:
  - DuckDB を主体としたデータ操作（全モジュールで DuckDB 接続を受け渡す設計）。
  - ロギング出力を各処理に実装（INFO / WARNING / DEBUG を適宜使用）。
  - トランザクション制御とロールバック保護（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK を試行しログ出力）。

Changed
- 初版のため該当なし。

Fixed
- JSON Mode の出力で前後に余計なテキストが混ざるケースに対して、最外の {} を抽出してパースする復元ロジックを追加（news_nlp のバリデーション処理）。
- OpenAI API エラー処理: APIError に status_code がある場合／ない場合を安全に扱い、5xx とそれ以外で挙動を分離。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- API キーの必須チェック: OpenAI API キー（環境変数 OPENAI_API_KEY または関数引数）が未設定の場合は ValueError を送出して明示的に失敗させる。
- 環境変数の自動ロードでは OS 環境変数を protected として上書きから保護。
- .env 読み込み失敗時は警告を出して安全にフォールバック。

Notes / 設計方針の要約
- ルックアヘッドバイアス対策: いずれのスコア/判定処理も内部で datetime.today()/date.today() を直接参照せず、呼び出し側から渡された target_date を基準に処理する設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出しに失敗しても処理全体を致命的に停止させず、スコアを 0.0 にフォールバックする等の安全策を採用。
- 冪等性: DB への書き込みは基本的に冪等（DELETE → INSERT / ON CONFLICT 的処理想定）で部分失敗時に既存データを不必要に消さない設計。
- テスト容易性: _call_openai_api 等をモジュール内で関数化し、unittest.mock.patch による差し替えを想定した実装。

---

将来のリリースでは以下を予定:
- strategy / execution / monitoring の詳細実装（注文・発注ロジック、監視エージェント）
- パフォーマンスチューニング（大規模データ時のクエリ最適化、並列化）
- より細かな品質チェック・自動アラート機構の追加

（この CHANGELOG はコード構成・コメントおよびソースから推測して作成しています。実際のリリースノートに合わせて追記・修正してください。）