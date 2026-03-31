# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。セマンティック バージョニングを採用しています。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初回リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - OS 環境変数を保護する protected 機能を実装し、.env.local による上書きをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、無効行のスキップなどに対応。
  - 必須環境変数取得メソッド _require を提供（未設定時は ValueError を投げる）。
  - 各種設定プロパティを提供 (J-Quants / kabu API / Slack / DB パス / 監視設定 / 環境・ログレベル判定等)。
  - KABUSYS_ENV と LOG_LEVEL の値チェック実装（無効値は ValueError）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成、OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
    - チャンク処理（最大 20 銘柄／回）、1 銘柄あたりの記事上限・文字数トリム、JSON mode による厳密な JSON 出力想定。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで処理。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。
    - DuckDB への冪等書き込み（DELETE→INSERT）、部分失敗時に既存スコアを保護する設計。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
    - calc_news_window: JST のニュース収集ウィンドウ計算ユーティリティを提供（UTC naive datetime を返す）。
    - score_news: 指定日付のニューススコアを ai_scores テーブルへ保存し、書き込んだ銘柄数を返却。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない設計）。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - リトライ／指数バックオフ、レスポンスパースの保護、ログ出力を実装。
    - score_regime は API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。

- データプラットフォーム (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL のフェッチ数・保存数・品質問題・エラーの集計）。
    - 差分更新・バックフィル設計、品質チェックとの連携設計を実装（jquants_client / quality モジュールを想定）。
    - DuckDB との互換性に配慮した実装（executemany に空リストを渡さないチェック等）。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジックと夜間バッチ更新(calendar_update_job) を提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のユーティリティ実装。
    - DB データ優先・未登録日は曜日ベースフォールバック、最大探索上限で無限ループを防止。
    - calendar_update_job は J-Quants API から差分を取得し冪等保存、バックフィルと健全性チェックを実装。
    - DuckDB 日付型の取り扱い変換ユーティリティ _to_date を提供。

- リサーチ（因子計算・特徴量探索） (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev) の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0/NULL の場合は None）。
    - すべて DuckDB 上の prices_daily / raw_financials を参照し外部 API 非依存で計算。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank: 平均ランクを用いるランク関数（同順位は平均ランク、丸め処理で ties の判定安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research/__init__.py で主要関数を再エクスポート。

### 変更（設計／実装上の重要事項）
- 全体方針（AI・リサーチ・ETL）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部ロジックで直接参照しない設計を明示（target_date を引数として受ける関数群）。
  - 外部 API 失敗時は例外で中断せずフォールバックやスキップを行うフェイルセーフ設計（監査ログ・警告は出力）。
  - DuckDB のバージョン差分に配慮した実装（例: executemany の空リスト回避、ANY バインドの互換性回避）。
  - OpenAI 呼び出しは JSON 出力前提（JSON mode）としつつ、パース失敗時にロバストな復元処理（先頭末尾の {} 抽出等）を実装。

- 環境読み込みの優先度と保護
  - 優先度: OS 環境変数 > .env.local > .env。OS 環境変数は protected set により .env による誤上書きを防止。
  - .env.local は override=True により .env を上書き可能で、テストやローカル調整を想定。

### 修正（不具合修正 / 安全対策）
- OpenAI / 外部 API 呼び出し周りに対して詳細な例外処理とリトライロジックを導入:
  - RateLimitError / APIConnectionError / APITimeoutError に対する指数バックオフと再試行。
  - APIError の status_code に基づく 5xx のみ再試行、それ以外は即スキップ。
  - JSON パース失敗や予期しないレスポンス時に安全にフォールバック（0.0 や空辞書を返す）。
- DB 書き込み時のトランザクションで ROLLBACK 時の失敗ログを追加し、上位に例外を再送出する一貫したエラーハンドリングを実装。
- market_calendar の欠損や NULL 値に対して警告ログを出すことで運用上の不整合を検知しやすく改善。

### 注意事項 / 既知の制約
- OpenAI API 使用:
  - API キーは score_news / score_regime の引数で注入可能。引数未指定時は OPENAI_API_KEY 環境変数を参照。未設定時は ValueError を送出する。
  - モデルは gpt-4o-mini を想定し、JSON Mode を利用する前提。実際 API の挙動やモデル更新によりパース処理の調整が必要になる可能性あり。
- DuckDB 互換性:
  - executemany に空リストを与えるとエラーとなるバージョンの考慮を行っているため、DuckDB のバージョン差に注意。
- 時間帯・タイムスタンプ:
  - ニュースのウィンドウ計算は JST を基準にし、DB クエリは UTC naive datetime を想定している。DB に格納された raw_news.datetime は UTC である前提。
- 安全・テスト性:
  - OpenAI API 呼び出し点（_call_openai_api）はユニットテストでパッチ可能にしてあり、実運用時の外部依存を分離可能。

---

今後のリリースでは、以下の点を改善・追加予定:
- jquants_client / quality モジュールの具体的実装・統合テスト
- 発注（execution）モジュールやモニタリング機能の公開 API の実装
- パフォーマンス計測および大規模データセットに対する最適化
- テストカバレッジの拡充（特に OpenAI レスポンスパース・DB 書き込み周り）

---