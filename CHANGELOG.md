CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" のスタイルに準拠しています。  
コードベースの内容から推測して作成しています（初期公開リリース相当）。

0.1.0 - 2026-04-01
-----------------

Added
- パッケージ初期リリースとして以下主要機能を実装・公開。
  - 基本パッケージ情報
    - kabusys.__version__ = "0.1.0" を設定。
  - 環境設定管理（kabusys.config）
    - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式・クォート・インラインコメント対応の堅牢な .env パーサ実装。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数チェック（_require）と Settings クラスによるプロパティアクセス
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を想定。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。
    - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）や監視設定（PID_FILE_PATH、閾値等）。
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合・トリムし、
      OpenAI（gpt-4o-mini）を用いたセンチメント（-1.0〜1.0）評価を実装。
    - バッチ処理（1コール最大20銘柄）、1銘柄あたりの最大記事数/文字数制限。
    - JSON Mode を利用した厳密な JSON 出力期待とパース回復処理（前後ノイズの {} 抽出）。
    - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンス検証とスコアのクリップ。部分成功時の DB 置換ロジック（DELETE→INSERT）で冪等性確保。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）と
      マクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - LLM 呼び出しはフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出し用にリトライ・エラーハンドリングを実装。
  - データプラットフォーム（kabusys.data）
    - カレンダー管理（calendar_management）
      - market_calendar を使った営業日判定（is_trading_day 等）、next/prev_trading_day、get_trading_days、is_sq_day を実装。
      - market_calendar が未登録のときは曜日ベース（週末除外）のフォールバックを採用。
      - JPX カレンダーを J-Quants から差分取得して保存する夜間ジョブ（calendar_update_job）を実装。
      - 健全性チェック・バックフィルロジックを組み込み。
    - ETL パイプライン（pipeline / etl）
      - ETLResult dataclass を公開（取得件数／保存件数／品質問題／エラーの集約）。
      - 差分取得、保存（idempotent）、品質チェックの設計を反映。
      - jquants_client を介した取得/保存の呼び出し箇所を想定。
    - ETL 実装は DuckDB を前提に SQL と Python を組み合わせて実装（prices_daily / raw_financials / raw_news 等を参照）。
  - リサーチ（kabusys.research）
    - ファクター計算（factor_research）
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER, ROE）等を実装。
      - データ不足時の None 扱い、sales/volume 等の流動性指標。
    - 特徴量探索（feature_exploration）
      - 将来リターン計算（複数ホライズン対応、デフォルト [1,5,21]）、IC（Spearman rank）計算、ランク関数、ファクターサマリを実装。
      - pandas に依存しない純標準ライブラリ実装。
  - 監視・実行・モニタリングに関するエクスポート（パッケージ __all__ に data, strategy, execution, monitoring を含める）。

Changed
- なし（初版リリース想定）。ただし下記設計選定事項を明記。
  - ルックアヘッドバイアス防止のため、多くの関数が datetime.today()/date.today() を参照せず target_date を引数に取る設計。
  - OpenAI 呼び出しや外部 API は失敗時に処理継続（フェイルセーフ）する方針を採用。

Fixed
- なし（初版）。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数に API トークンやパスワードを保持する想定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - .env/.env.local の読み込みと自動セット機能を提供するが、秘密情報管理は運用ルール（.gitignore, secrets manager 等）を推奨。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。

注意事項 / 既知の制約
- DuckDB に関する互換性
  - executemany に空リストを渡せない（DuckDB 0.10 の挙動）ため、空リストをチェックしてから executemany を呼ぶ実装上の配慮あり。
- OpenAI API
  - gpt-4o-mini + JSON Mode を想定（response_format による JSON オブジェクト取得）。
  - API レスポンスの前後ノイズ（JSON 以外テキストが混入するケース）を想定したパース回復ロジックを実装しているが、完全な安全性は保証されない。
- ルックアヘッドバイアス防止
  - 全ての主要スコアリング・ファクター計算は target_date を明示的に受け取り、target_date 未満・以前のデータのみを参照するよう設計されている。
- 部分的失敗時の保護
  - 複数銘柄をまとめて処理する際、一部銘柄の API 呼び出し失敗で他銘柄の既存スコアを消さないよう、書き込みはスコア取得済みコードに限定して行う設計。

移行／導入メモ
- 必須環境変数を設定してください（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- プロジェクトルートに .env/.env.local を置くことで自動読み込みされます。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動ロードを無効化可能です。
- DuckDB のバージョンや OpenAI の SDK 仕様変更に伴う挙動差分が将来発生する可能性があります（特に APIError の status_code 取り扱い等に注視）。

今後の予定（想定）
- API 呼び出しのモック・テスト補強、より詳細な品質チェック・アラートルールの実装。
- ストラテジー実行部分（戦略定義 → 注文執行）・監視周りの拡張（現在はパッケージ構成に名前空間を準備済み）。
- ファクター・リサーチ機能の追加（PBR、配当利回りなど）。

----- 

この CHANGELOG はコードから推測して作成したため、実際のコミット履歴や設計意図と差異がある可能性があります。必要であれば実際の git コミットログやリリースノートに基づいて調整します。