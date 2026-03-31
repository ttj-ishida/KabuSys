CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現状、リポジトリ内のコードに基づく最初の公式リリースを作成しました。今後の変更はこのセクションに記載してください。）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース "KabuSys" を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - エクスポート: data, strategy, execution, monitoring を __all__ として公開準備。

- 環境設定/ローダー (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート .git または pyproject.toml を検出してそこを基準に読み込み）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無での扱い差）に対応。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）の検証
    - is_live / is_paper / is_dev ユーティリティプロパティ
  - 必須環境変数未設定時は明示的な ValueError を送出。

- AI 関連機能 (src/kabusys/ai/)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して、銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC で扱う calc_news_window）。
    - バッチ処理（デフォルト _BATCH_SIZE=20）、1銘柄あたりの記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ポリシー: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数設定）。
    - レスポンス検証と抜け対策（JSON mode の余計な前後テキストへの耐性）、スコアを ±1.0 にクリップ。
    - DB への書き込みは冪等処理（該当 date と code の DELETE → INSERT、部分失敗時に他コードのスコア保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api をパッチ可能）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - MA200 比率算出、マクロキーワードで raw_news をフィルタし LLM でセンチメント算出、両者を合成してクリップ／閾値判定。
    - OpenAI 呼び出しに対して堅牢なリトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0 として継続）。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。

- データ基盤ユーティリティ (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）を採用。
    - 最大探索日数制限、バックフィル・先読み設定、健全性チェックを実装。
    - calendar_update_job により J-Quants クライアントを使った差分取得 → 保存の夜間ジョブを想定（jquants_client を利用）。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL の設計文書に基づく差分取得・保存・品質チェックフローを実装方針として実装（ETLResult データクラスを公開）。
    - ETLResult により取得数・保存数・品質チェック結果・エラーの集約と to_dict 出力を提供。
    - テーブル存在確認や最大日付取得などのユーティリティを実装。
    - デフォルトのバックフィル挙動、カレンダーヘルパー、DuckDB 利用前提で実装。
  - data パッケージの公開インターフェースを整理（ETLResult 再エクスポートなど）。

- リサーチ（因子解析） (src/kabusys/research/)
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー等の定量ファクターを実装:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None / 中立処理）。
      - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
      - calc_value: raw_financials と prices_daily を組み合わせ PER / ROE を算出（EPS が 0/欠損なら None）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。関数は prices_daily / raw_financials のみを参照。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（デフォルト [1,5,21]）。ホライズン値検証あり。
    - calc_ic: スピアマンのランク相関に基づく IC を実装（同値の扱いは平均ランク）。
    - rank: ties を平均ランクで扱う安定したランク変換実装（丸めによる ties 対策）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

Changed
- 初期リリースなので "Changed" は特に無し（将来のリリースで履歴を追記）。

Fixed
- 初期リリースなので "Fixed" は特に無し。

Security
- 環境変数取り扱いに注意を促す記載:
  - 必須トークン（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN）は安全に管理すること。
  - .env の自動読み込みは開発支援目的。プロダクション環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を活用すること。

Notes / 注意事項
- 依存・前提
  - DuckDB によるローカルデータストアを利用する設計（src 内 SQL が DuckDB を前提）。
  - OpenAI の Chat Completions（gpt-4o-mini + JSON mode）を使用。API 呼び出しはネットワーク上の外部依存。
  - jquants_client（DataPlatform 側クライアント）や kabu API クライアントは外部モジュールとして想定され、実装は別途必要。
- フェイルセーフ設計
  - LLM 呼び出しの失敗は概ねフォールバック（0.0）やスキップで処理継続する設計。ETL・AI 関連で部分失敗しても他データを保護する仕組み（部分的な DELETE→INSERT、書き込み前の空チェック等）を採用。
- テスト支援
  - OpenAI 呼び出し用の内部関数はテストで差し替え可能（unittest.mock.patch を想定）。
- 将来的なモジュール展開
  - __all__ に strategy / execution / monitoring が含まれていることから、自動売買実行・監視・ストラテジ実装向けのモジュール追加が想定される。

Migration / 必要な環境変数（リリース 0.1.0）
- OPENAI_API_KEY (AI 機能利用時)
- JQUANTS_REFRESH_TOKEN (J-Quants API 利用)
- KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知機能）
- DUCKDB_PATH / SQLITE_PATH は省略可能（デフォルトを使用）

既知の制限 / TODO（推定）
- strategy / execution / monitoring の具象実装は未確認（パブリック API の足がかりあり）。
- 一部の外部クライアント（jquants_client, kabu クライアント）の具体実装は別リポジトリまたは別モジュールを想定。
- 現行実装は DuckDB 固有の挙動（executemany の空リスト問題、リストバインドの不安定さ）を回避するために注意深く実装されているが、DuckDB の異なるバージョンでの互換性は要検証。

クレジット
- この CHANGELOG はリポジトリ内のソースコードを読み取り、機能・設計方針・安全性・既知制限を推測して作成しました。実際の変更履歴と差異があればお知らせください。