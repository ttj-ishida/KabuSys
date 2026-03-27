# CHANGELOG

すべての注目すべき変更を追跡します。  
このプロジェクトは Keep a Changelog の形式に概ね準拠しています。  

なお、本CHANGELOGはリポジトリ内のソースコードから機能・設計を推測して作成しています。

## [Unreleased]
（現時点の開発中変更はここに記載します）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムのコアライブラリを実装。

### 追加 (Added)
- パッケージ公開
  - kabusys パッケージを公開。バージョンは 0.1.0。
  - __all__ に "data", "strategy", "execution", "monitoring" を設定。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env の行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得可能に
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（valid: development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）検証
    - is_live / is_paper / is_dev ヘルパー

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む score_news(conn, target_date, api_key=None) を実装。
    - JST 基準のニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window(target_date) で算出。
    - 1チャンクあたり最大 20 銘柄でバッチ送信、1銘柄当たり最大記事数/文字数でトリム。
    - OpenAI JSON Mode を使った厳密な JSON レスポンスを期待しつつ、前後の余計なテキスト混入へのロバスト化（最外の {} を抽出して再パース）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（results 配列、code/score の存在、未知コードの無視、数値チェック、スコア ±1.0 クリップ）。
    - 部分成功を想定し、書き込みは該当コードに対して DELETE → INSERT の置換方式（idempotent）で実施。DuckDB の executemany 制約を考慮。
    - テスト容易性のため _call_openai_api を patch 可能に（unittest.mock.patch 用）。
    - API キーの解決は引数優先、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
    - prices_daily からの MA 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - raw_news からマクロ関連キーワードでフィルタしたタイトルを抽出し、OpenAI で macro_sentiment を評価（記事なしまたはAPI失敗時は macro_sentiment=0.0 のフェイルセーフ）。
    - レジームスコアは定数スケーリングとクリッピング後に閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）。
    - 結果は market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込む。
    - OpenAI 呼び出しでのリトライ／エラーハンドリングを実装。テスト用に _call_openai_api を差し替え可能。

- 研究（Research）モジュール
  - kabusys.research.* を実装・再エクスポート
    - factor_research.calc_momentum / calc_value / calc_volatility
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
      - Value: latest raw_financials と当日株価から PER/ROE を計算
      - Volatility/Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率
      - DuckDB の Window 関数を活用した実装
    - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
      - 将来リターン（任意ホライズン）を効率的に取得する calc_forward_returns
      - スピアマン（ランク）ベースの IC を calc_ic で実装（ペア数が 3 未満なら None）
      - rank は同順位処理を平均ランクで扱う実装
      - factor_summary で count/mean/std/min/max/median を算出
    - kabusys.data.stats.zscore_normalize を再エクスポート（__init__ で使用）

- データ基盤（Data）モジュール
  - calendar_management
    - JPX マーケットカレンダーを扱うユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants API から差分取得 → jq.save_market_calendar で idempotent に保存（バックフィルと健全性チェック含む）。
  - pipeline / etl
    - ETLResult データクラスを提供（取得数／保存数／品質問題／エラーの集約）。
    - 差分取得・バックフィル・品質チェックの設計方針をコードとして実装（jquants_client と quality モジュール連携を想定）。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得等を提供。
  - etl の公開インターフェースとして ETLResult を再エクスポート（kabusys.data.etl）

- ロギング・フォールバック設計
  - 多くのモジュールで失敗時に例外を破棄せずフェイルセーフ（ゼロや空辞書で継続）し、警告/情報ログを出力する設計を採用。
  - データベース書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時は警告を出す。

### 変更 (Changed)
- （初版のため変更履歴はなし）

### 修正 (Fixed)
- （初版のため修正履歴はなし）

### 削除 (Removed)
- （初版のため削除履歴はなし）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で注入可能。環境変数利用は開発運用上の利便性のために残すが、テストや CI では引数注入や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化でキーの漏洩や副作用を回避できる設計。

---

備考（実装上の重要点・設計判断）
- ルックアヘッドバイアス防止: 多くの関数が datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- DuckDB を主要なローカルデータストアとして想定。SQL は Window 関数を用いて効率的に計算。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用する想定だが、実際の SDK 挙動や前後テキスト混入に備えたパース処理を追加。
- テスト容易性のため外部呼び出し（OpenAI）を差し替えられるフックを用意。

今後の予定（推測）
- strategy / execution / monitoring パッケージの実装（パッケージは __all__ に存在するが本リリースでは中身が見当たらない）。
- jquants_client、quality モジュールの具体実装と連携テスト。
- CI / ユニットテスト拡充、モックを利用した OpenAI との連携テスト。

もし特定の変更点やより詳細な説明（例えば各関数のサンプル使用例、期待されるDBスキーマなど）をCHANGELOGに追記したい場合は指示してください。