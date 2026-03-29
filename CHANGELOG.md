# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースの現在の状態（ソースから推測）に基づく初期リリース向けの変更履歴です。

全般的な方針:
- バージョンはパッケージ内の __version__（0.1.0）に合わせています。
- 日付はこの出力作成日（2026-03-29）を使用しています（実際の公開日で適宜更新してください）。
- 各項目はモジュール単位で主な追加機能、設計上の注意、フェイルセーフや互換性対策を記載しています。

Unreleased
---------
- （なし）

0.1.0 - 2026-03-29
-----------------
Added
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, monitoring, strategy, execution など想定）を __all__ で公開。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みするユーティリティを追加。
    - プロジェクトルートは .git または pyproject.toml を基準に自律的に探索（CWD に依存しない）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS側に存在する環境変数は保護（protected）され、上書き回避。
  - .env パーサ実装（_parse_env_line）:
    - export KEY=val 形式対応、シングル/ダブルクォート内部のバックスラッシュエスケープ対応。
    - クォート無し時のインラインコメント解析（'#' の直前がスペース/タブの場合のみコメント扱い）。
  - Settings クラスを提供し、主要設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトローカルホスト）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
    - DB パス設定（DUCKDB_PATH / SQLITE_PATH）を Path として返却。
    - KABUSYS_ENV の検証（development / paper_trading / live のいずれか）と LOG_LEVEL の検証。
    - ユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）でニュースを銘柄別に集約して OpenAI（gpt-4o-mini）に送り、銘柄ごとのセンチメント（-1.0～1.0）を ai_scores テーブルへ保存する score_news を実装。
    - バッチ処理：1回の API 呼び出しで最大 20 銘柄を処理（_BATCH_SIZE）。
    - 1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化を防止。
    - JSON Mode を利用しレスポンスを厳密にパース。汚染テキストが混入した場合は最外側の {} を抽出して復元を試みる。
    - 失敗耐性：429・接続断・タイムアウト・5xx を指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ）。
    - バリデーション：results の型・各要素の code/score の整合性チェック、スコアの ±1.0 クリップ。
    - DB 書き込み: 成功したコードのみを対象に DELETE → INSERT（部分失敗時に他コードの既存データを保護）。DuckDB の executemany の制約（空リスト不可）に配慮。
    - テスト容易性のため、OpenAI 呼び出し部分は内部関数をパッチ可能にしてある。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で market_regime を算出する score_regime を実装。
    - news_nlp と同様に gpt-4o-mini を用いるが、OpenAI 呼び出し実装は独立（モジュール結合を避ける）。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。
    - レジームスコアは -1.0～1.0 にクリップし、閾値に基づき bull/neutral/bear にラベリング。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行、失敗時はROLLBACK。

  - 両モジュール共通の設計方針:
    - datetime.today() / date.today() を内部で参照せず、明示的な target_date を受け取ることでルックアヘッドバイアスを防止。
    - OpenAI API 呼び出しはテストで差し替えられるよう設計。

- 研究（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から直近財務データを取得して PER（EPS がない/0 の場合は None）、ROE を算出。
    - DuckDB SQL を中心に実装し、prices_daily / raw_financials のみ参照。出力は (date, code) を含む dict のリスト。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（IC）を計算（ペア数が3未満は None）。
    - rank: 同順位は平均ランクを割り当てる実装（丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を集計。None 値は除外。
  - 依存: 可能な限り標準ライブラリと DuckDB のみを使用（pandas 等に依存しない設計）。

- データ（kabusys.data）
  - calendar_management:
    - market_calendar を元に営業日判定や next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを提供。
    - DB 登録がない場合は曜日ベース（土日を非営業日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants クライアント経由で差分取得・バックフィル（直近 _BACKFILL_DAYS を再取得）を行い、冪等保存を実施。健全性チェック（将来日付異常検出）を実装。
    - 最大探索範囲・安全策（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS）を設定して無限ループや異常データを防止。
  - pipeline（ETL）:
    - ETLResult データクラスを導入し、ETL の集計結果（取得件数・保存件数・品質問題・エラー）を表現。
    - 差分更新ロジック、バックフィルポリシー、品質チェックの扱い方針をコードレベルで反映。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを提供。
  - etl モジュールは ETLResult を再エクスポートして外部使用を簡便化。

- テスト容易性 / 運用面の配慮
  - OpenAI 呼び出し（内部関数）を unittest.mock.patch で差し替え可能に設計。
  - DuckDB のバージョン依存（executemany に空リスト不可）への互換性回避策を実装。
  - ロギングを要所に追加し、失敗時の情報やフォールバックを明示。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- ユーザーに明示: OpenAI API キー等の機密は環境変数で管理すること。Settings は必須鍵未設定時に ValueError を投げるため、デプロイ時に必要な環境変数の設定が必須。

Notes / 既知の設計上の注意
- 多くの処理で「フェイルセーフ」戦略（API 失敗時はスコアを 0.0 として継続、もしくは該当チャンクをスキップ）を採用しており、部分的なデータ欠損・API 障害がシステム全体を停止させない設計になっています。ただし、その結果として一時的にスコアが中立化される可能性があります。
- 各種日時ロジックは target_date を明示的に受け取ることでルックアヘッドバイアスを防止しています。運用時は target_date の供給方法に注意してください。
- DuckDB による SQL 実行では型やNULLの扱いに注意（例: date 型の取り扱い、NULL の扱いによる集計の違い）。
- .env パーサは一般的な shell 形式をサポートしますが、極端に複雑な .env の書き方（多重引用符や複雑なエスケープ）には注意が必要です。

今後の改善候補（推奨）
- ai モジュールのユニットテスト用にモックサーバやレスポンス再現機構を整備すると信頼性向上に寄与します。
- ETL の実行ログ・監査ログをより詳細に保存する仕組み（例: ETLResult の永続化）を追加すると運用性が向上します。
- cron / CI/CD での自動デプロイ時に必要な environment variable ドキュメントの整備（.env.example の整備）を推奨します。

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース履歴や公開日、追加/修正内容はプロジェクトの公式記録に合わせて適宜更新してください。）