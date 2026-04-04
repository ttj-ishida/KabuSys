# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは与えられたコードベースの実装内容から推測して作成しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買データプラットフォーム / 研究・AI支援モジュールを含む基本機能を実装。

### 追加 (Added)
- パッケージ公開
  - kabusys パッケージを追加。トップレベルの公開モジュールは data, strategy, execution, monitoring（__all__ に定義）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（プロジェクトルート探索: .git / pyproject.toml を起点に検索）。
  - .env パーサーは以下に対応:
    - 行頭の `export ` プレフィックス
    - シングル/ダブルクォートとバックスラッシュによるエスケープ
    - クォートなし時のインラインコメント処理（`#` の直前が空白の場合にコメントと判定）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数を保護するための上書き（override）ロジックを導入（`.env.local` を優先して読み込む実装）。
  - 必須値取得ヘルパー `_require` と、Settings クラスを提供。以下の設定プロパティを実装:
    - J-Quants / kabu API / LINE Messaging / データベース（duckdb/sqlite）パス
    - 実行監視用 PID/KILL フラグパス・閾値（CPU/MEM/DISK）
    - 環境（development / paper_trading / live）とログレベル検証
    - is_live / is_paper / is_dev のブール判定

- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール: score_news を実装（raw_news と news_symbols を集計して OpenAI に一括バッチ送信 → ai_scores に書き込み）。
    - JST ベースのニュースウィンドウ計算 calc_news_window を提供（前日 15:00 JST 〜 当日 08:30 JST の範囲）。
    - バッチサイズ、記事数・文字数上限、OpenAI JSON mode を利用した堅牢な API 呼び出し実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ実装。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - 部分失敗を許容する安全な DB 書き込み（対象コードのみ DELETE → INSERT）により他コードの既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し関数は patch 可能（_call_openai_api を分離）。
  - regime_detector モジュール: score_regime を実装（ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定）。
    - ma200_ratio の計算（target_date 未満のデータのみ参照してルックアヘッドバイアスを回避）。
    - マクロニュースはキーワードでフィルタ（最大記事数制限）。
    - OpenAI 呼び出しは gpt-4o-mini を利用、JSON 出力を期待してパース。
    - マクロ API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成（重み: MA70% / Macro30%、スコアクリップ）とラベル付け（bull/neutral/bear）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK ログ処理。
    - API 呼び出しのテスト差替え用の分離実装（_call_openai_api）。

- リサーチモジュール (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を算出。
    - 各関数は DuckDB 上の SQL クエリで計算し、(date, code) をキーとする dict のリストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装（コードで結合、None/非有限値除外、3件未満は None を返す）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティをパッケージ外から利用しやすくエクスポート。

- データプラットフォーム (src/kabusys/data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job: J-Quants クライアント経由で差分取得し冪等的に保存。バックフィル・健全性チェックを実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
  - ETL / pipeline:
    - ETLResult データクラスを追加（pipeline モジュールの結果表現）。ETL 実行で取得件数・保存件数・品質問題・エラーを保持。
    - Pipeline 層の設計に合わせ、差分取得・保存（idempotent）・品質チェックの基本方針を実装（jquants_client / quality モジュールとの連携想定）。
    - etl.py で ETLResult を再エクスポート。

- パッケージ公共 API の調整
  - ai, research, data など主要サブパッケージで公開関数/シンボルを __all__ で定義している箇所を追加。

### 変更 (Changed)
- 実装方針・堅牢性の確保
  - すべての AI/研究処理で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しの再試行・パース失敗時のフェイルセーフ動作（例外を上げずデフォルト値を使って継続）を採用。
  - DuckDB の executemany に対する互換性（空リスト不可）に配慮した DB 書き込みロジック。

### 修正 (Fixed)
- API レスポンス・DB書き込みにおけるエラー処理の明確化
  - DuckDB トランザクションでの例外時に ROLLBACK を試行し、ROLLBACK 自体の失敗をログに記録するように変更。
  - OpenAI API の APIError について status_code の有無に対応（getattr を利用）して 5xx の扱いを判別。

### 注意事項 / 既知の制約 (Notes / Known issues)
- 外部依存
  - AI 機能 (score_news / score_regime) は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
  - データ取得・更新には J-Quants 関連の環境変数（例: JQUANTS_REFRESH_TOKEN）が必要。
  - DuckDB を想定したスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等）が存在することが前提。
- 動作上の設計選択
  - API 呼び出し失敗時は多くのケースで「0.0 にフォールバック」または「スキップして継続」としており、可用性を優先する設計。厳格な失敗検出が必要な場合は呼び出し元で検査すること。
  - news_nlp のレスポンスパースは JSON mode を期待するが、前後に余計なテキストが混じるケースに備え最外の {} を抽出して復元を試みる処理を含む。
  - calendar_update_job は J-Quants クライアント (kabusys.data.jquants_client) の実装に依存するため、実環境では当該クライアントの動作確認が必要。
- テスト性
  - OpenAI 呼び出しは内部で分離されており、ユニットテスト時に patch 可能（_call_openai_api の差替え）。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化でき、テスト環境での環境変数制御に配慮。

### セキュリティ (Security)
- 特記事項なし。ただし API キー / パスワード（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）は環境変数で管理する前提。取り扱いに注意。

---

今後のリリース候補（例）
- 0.2.0: 発注実行・監視（execution / monitoring）モジュールの実装、Strategy モジュールの追加、テストカバレッジ拡張
- 0.1.x: バグ修正、J-Quants クライアントや DB スキーマ互換性の改善

もし特定の変更点（コミットメッセージ等）を反映したい場合は、該当の履歴や意図を教えてください。