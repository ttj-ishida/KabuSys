CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。

- 環境設定／ロード機能（kabusys.config）
  - .env ファイルまたは既存の環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト目的に便利）。
    - OS 環境変数を保護するため保護キーセットを導入し、override オプション時でも上書き除外可能。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（直前がスペース/タブの場合のみ）
  - Settings クラスを公開（settings = Settings()）:
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）
    - 各種パスは Path オブジェクトで返却（expanduser 対応）
    - ライブ・ペーパー・開発判定ユーティリティ: is_live / is_paper / is_dev

- ニュースNLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None) を実装:
    - 指定ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づき raw_news と news_symbols から銘柄ごとに記事を集約。
    - 1銘柄あたり最新 _MAX_ARTICLES_PER_STOCK（デフォルト 10）記事を結合し、文字数は _MAX_CHARS_PER_STOCK（3000）でトリム。
    - OpenAI の gpt-4o-mini（JSON Mode）へ最大 _BATCH_SIZE（20）銘柄ずつバッチ送信。
    - レスポンスは JSON の "results" 形式を期待し、各要素 {code, score} を抽出。スコアは ±1.0 にクリップ。
    - 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対しては指数バックオフでリトライ。非リトライ系エラーやパース失敗はログ出力の上スキップ（フォールセーフ）。
    - DuckDB への書き込みは冪等処理（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。DuckDB executemany の空リスト制約に対応。
    - API キー注入可（引数優先、無ければ環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError。

  - 内部ユーティリティ:
    - calc_news_window(target_date): target_date に対する UTC naive のウィンドウ計算（JST ベースの説明付き）。
    - レスポンスバリデーション関数（JSON 抽出、型チェック、未知コード無視、有限値チェック）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を実装:
    - ETF 1321 の 200 日移動平均乖離（_MA_WINDOW=200）を計算し（_calc_ma200_ratio）、重み 70% でレジームに寄与。
      - データ不足（200 日未満）時は中立（1.0）を返し WARNING ログ。
      - ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用。
    - raw_news からマクロ経済キーワードでフィルタしたタイトルを抽出（_fetch_macro_news）。
    - gpt-4o-mini を用いてマクロセンチメントを -1.0〜1.0 で評価（_score_macro）。記事がない場合は LLM 呼出しをスキップし macro_sentiment=0.0。
    - マクロ（30%）とMA乖離（70%）を合成して regime_score を算出、閾値により 'bull'/'neutral'/'bear' ラベル化。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE WHERE date=? / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行し例外を伝播。
    - OpenAI API の再試行ポリシーや 5xx の扱いなどフェイルセーフ実装あり。API キー注入可（引数優先、環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError。

- 研究用ファクター・特徴量探索（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev（200日MA乖離率。200 行未満は None）を計算。
    - calc_volatility(conn, target_date): atr_20（20日 ATR 平均）、atr_pct、avg_turnover（20日）、volume_ratio（当日/20日平均）を計算。true_range は high/low/prev_close が NULL の場合 NULL を伝播させる実装。
    - calc_value(conn, target_date): raw_financials の最新財務（report_date <= target_date）を取得し PER（EPS が 0 または欠損時は None）、ROE を算出。price と結合して返却。
    - すべて DuckDB クエリ中心で実装し、外部 API 呼び出しや発注等の副作用は一切なし。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): LEAD を用いて将来終値との差分リターンを一括取得。horizons の検証あり（正の整数かつ <=252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を実装。3 件未満で None を返却。
    - rank(values): 同順位は平均ランクを返す実装（round で数値丸め処理し ties を安定検出）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算（None 除外）。

  - research パッケージの __all__ により主要関数を公開（zscore_normalize は kabusys.data.stats から再利用）。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベースでフォールバック（週末を非営業日）。
      - DB 登録値優先、未登録日は曜日フォールバックで一貫した振る舞いを保証。
      - next/prev_trading_day の探索上限 (_MAX_SEARCH_DAYS) を設定し無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API（jquants_client.fetch_market_calendar）から差分取得し market_calendar を冪等保存。バックフィル（直近 _BACKFILL_DAYS）や健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult dataclass を実装（結果要約・品質問題・エラー情報の集約、to_dict メソッドあり）。
    - ETL パイプライン設計方針とユーティリティ関数（テーブル存在チェック・最大日付取得など）の基礎を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

Changed
- （初回リリースのため過去バージョンとの差分はなし）
- 設計上の重要な方針を明記:
  - すべての日次判定やスコア算出は datetime.today()/date.today() を直接参照せず、外部から渡す target_date に依存して実行（ルックアヘッドバイアス回避）。
  - OpenAI 呼び出しはモジュール間で private 関数を共有せず、各モジュールが独自の _call_openai_api を持つことで結合度を下げ、テストでの差し替えを容易化。
  - API エラー時はフェイルセーフ（スコア 0.0 や該当銘柄スキップ）で継続する設計。
  - DuckDB の executemany に空リストを渡せないバージョン互換性を考慮して条件分岐を実装。

Fixed
- （初回リリースのため過去バージョンからの不具合修正はなし）

Security
- 環境変数読み込みで OS 環境変数を保護する仕組みを導入（protected set）。自動ロードは明示的フラグで無効化可能。
- OpenAI API キーの取り扱いは引数注入または環境変数を期待し、未設定時は例外を送出することでキーなし実行を防止。

Notes / Implementation details
- OpenAI モデル: gpt-4o-mini を想定（JSON Mode を利用）。
- DuckDB を主要なローカルデータストアとして想定。クエリはパフォーマンスを意識してウィンドウ関数や部分スキャンを活用。
- ロギング: 各モジュールで logger を利用して情報・警告・例外を出力するように実装。
- テスト容易性:
  - OpenAI 呼び出しはモック可能（各モジュールの _call_openai_api を unittest.mock.patch により差し替え可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト実行時の副作用（.env 自動ロード）を制御可能。

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から推測して記載しています。実際の API キーや外部依存（J-Quants, OpenAI）動作は環境やバージョンに依存します。