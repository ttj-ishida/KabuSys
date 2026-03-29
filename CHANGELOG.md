# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
初期リリースは以下の通り、ソースコードから実装・設計意図を推測して記載しています。

注意: 日付はこの CHANGELOG 作成時点（2026-03-29）を使用しています。

## [Unreleased]

（次回リリースでの変更をここに記載します）

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムの基礎モジュール群を実装しました。主な追加点、設計方針、外部依存・設定について以下にまとめます。

### 追加 (Added)

- パッケージメタ情報
  - kabusys パッケージ初期化（__version__ = "0.1.0"、公開サブパッケージ定義）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル / 環境変数からの設定読み込みを自動化。
  - プロジェクトルート検出（.git または pyproject.toml による探索）により、CWD に依存しない .env 自動読み込みを実現。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等）。
  - .env と .env.local の読み込み順序を定義（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）として扱う。
  - 読み込み保護（protected keys）機能を導入し OS 環境変数を上書きしないように保護。
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時の制御用）。
  - Settings クラスを提供し、アプリケーション設定プロパティを型付きで取得可能に:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
    - 環境（KABUSYS_ENV）のバリデーション（development/paper_trading/live のみ許容）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパープロパティ。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール（score_news）:
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode による一括センチメント評価を行い、ai_scores テーブルへ冪等的に書き込む。
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数上限でトークン肥大対策（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフとリトライ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code の正規化、数値チェック、スコアクリップ ±1.0）。
    - DuckDB の executemany における空リスト制約に対する回避処理（空のときは実行しない）。
    - 設計上、datetime.today()/date.today() を直接参照せず、target_date パラメータベースでルックアヘッドバイアスを防止。

  - regime_detector モジュール（score_regime）:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を統合して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う。
    - マクロニュース抽出のためのキーワードリストを内蔵（日本・米国の主要語句）。
    - OpenAI 呼び出しは専用実装で疎結合化。API エラー時はフェイルセーフで macro_sentiment = 0.0 を使用して継続。
    - 再試行・バックオフ、レスポンス JSON パースの堅牢化、5xx の扱いなどを実装。
    - ルックアヘッドバイアス防止（target_date 未満のみを参照）および冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- Research（因子分析） (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を prices_daily から計算（営業日ベースのラグ利用）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。true_range 計算で NULL 伝播を制御。
    - calc_value: raw_financials と prices_daily を組合せ PER/ROE を計算。最新財務レコードの取得は ROW_NUMBER を用いて安全に実装。
    - すべて DuckDB 上の SQL + Python で完結（外部 API にアクセスしない）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する効率的クエリ実装。ホライズン検証あり。
    - calc_ic: Spearman ランク相関（IC）を実装（不足データ・定数分散等は None を返す）。
    - rank: 同順位は平均ランクを与える実装（丸め処理で tie 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを標準ライブラリだけで提供。
  - kabusys.research パッケージから主要関数を再エクスポート。

- Data プラットフォーム (kabusys.data)
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB 登録済みの日付を優先、未登録日は曜日ベースのフォールバック（週末は非営業日）として一貫した挙動を実現。
    - カレンダーデータの夜間差分取得 job（calendar_update_job）を実装。バックフィル、健全性チェック（将来日付の異常検出）を含む。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL 実行結果（取得数/保存数/品質問題/エラー）を集約。
    - pipeline モジュールの ETLResult を data.etl で再エクスポート。
    - 差分取得・バックフィル・品質チェックを行う設計方針を実装前提で文書化（ソースに設計意図を明記）。
  - jquants_client / quality 等の外部クライアントや品質チェックモジュールを参照（本実装ではクライアント呼び出しポイントを利用）。

### 変更 (Changed)

- 初版リリースのため過去バージョンからの変更履歴はありませんが、以下の設計上の決定を公開版として確定しました:
  - OpenAI の出力は JSON mode 想定（response_format={"type":"json_object"}）で厳密な JSON を期待する設計。
  - LLM 呼び出しでの失敗は例外で直ちに上位に伝播させず、フェイルセーフ（スコア 0.0 や該当銘柄スキップ）で処理継続する方針。
  - DuckDB の互換性問題（executemany の空リスト不可等）に配慮した実装。

### 修正 (Fixed)

- なし（初回リリース）。ただし多くのエッジケース（API 失敗、JSON パースエラー、DB ロールバック失敗など）に対するログ出力とフェイルセーフ処理を含めて堅牢化しています。

### セキュリティ & 設定上の注意 (Security & Configuration)

- OpenAI API キーの扱い:
  - score_news / score_regime の両関数は api_key 引数または環境変数 OPENAI_API_KEY を必須とします。未設定時は ValueError を送出します。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など、Settings プロパティで必須と定義したキーが存在しない場合は ValueError。
- .env 自動読み込み:
  - デフォルトで自動ロード有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB 書き込み:
  - 各種書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定）して実装。失敗時は ROLLBACK を試み、失敗ログを記録。

### 既知の制約・今後の確認事項 (Known limitations / Future work)

- DuckDB バインド挙動:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）へ配慮したガードがあるものの、環境差異に注意。
- LLM モデル・API 依存:
  - 現時点で gpt-4o-mini + JSON mode を想定しているため、API/SDK の将来変更により調整が必要になる可能性あり。
- 一部外部モジュール（jquants_client, quality 等）はインターフェースを参照する形で組み込まれており、実運用時はそれらの実装提供が必要。
- パフォーマンス:
  - チャンク処理や SQL のスキャン範囲に関する調整はデータ規模に応じてチューニングが必要。

---

将来のリリースでは、ユニットテストの整備状況、API クライアントの抽象化、追加の品質チェックルール、さらに発注/実行モジュール（execution）や監視（monitoring）周りの実装状況に応じて CHANGELOG を更新していきます。