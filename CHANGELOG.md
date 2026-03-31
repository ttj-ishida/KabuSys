CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース (バージョン 0.1.0)
  - 基本パッケージ情報を追加
    - src/kabusys/__init__.py にパッケージ名と __version__ = "0.1.0" を定義。公開サブパッケージとして data, strategy, execution, monitoring を列挙。

- 環境設定 / .env ロード機能
  - src/kabusys/config.py を追加。
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）し、ワーキングディレクトリに依存せず自動 .env 読み込みを行う。
    - .env / .env.local の読み込み順序（OS > .env.local > .env）と、OS 環境変数を保護する protected キーの概念を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 複雑な .env の行パーシングに対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理）。
    - 必須環境変数取得用の _require、及び Settings クラスを実装：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値処理。
      - KABUSYS_ENV（development / paper_trading / live）の検証、LOG_LEVEL の検証、および is_live / is_paper / is_dev のユーティリティを提供。

- AI（Natural Language Processing）モジュール
  - src/kabusys/ai/news_nlp.py を追加（ニュース記事のセンチメント解析と銘柄別スコアリング）。
    - target_date に対するニュースウィンドウ計算（JST ベース → UTC 表現）を実装（calc_news_window）。
    - raw_news と news_symbols から銘柄別に記事を集約し、記事数と文字数の上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチスコアリング（最大 _BATCH_SIZE=20 銘柄/コール）。
    - 再試行/バックオフ処理（429, ネットワーク断, タイムアウト, 5xx 対応）と非致命的失敗時のフェイルセーフ（スキップして継続）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フィールド、code と score の検証、未知コードの無視、数値チェック）、およびスコアの ±1.0 でのクリップ。
    - DB 書き込みは部分失敗に強い設計（スコア取得済みコードのみ DELETE → INSERT）や DuckDB の executemany 空リスト制約への対策。
    - テスト向けに _call_openai_api のパッチ差し替えを想定した設計。
    - 公開関数: score_news(conn, target_date, api_key=None)

  - src/kabusys/ai/regime_detector.py を追加（市場レジーム判定）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース（LLM によるセンチメント、重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算するロジック（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - raw_news からマクロキーワードによるタイトル抽出（キーワード群を定義）と、OpenAI を用いた macro_sentiment スコア化（JSON mode、リトライ/バックオフ、フェイルセーフで 0.0 にフォールバック）。
    - レジームスコア合成、ラベリング閾値（BULL_THRESHOLD / BEAR_THRESHOLD）、および market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト向けに _call_openai_api を差し替え可能。
    - 公開関数: score_regime(conn, target_date, api_key=None)

  - src/kabusys/ai/__init__.py を追加し score_news を再エクスポート。

- Research（ファクター / 特徴量探索）モジュール
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の SQL と Python 組合せで計算する関数を提供。
    - 計算関数:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時の None 扱いや、営業日／スキャン範囲のバッファの設計について明確化。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、Information Coefficient（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）などを実装。
    - calc_ic はスピアマンのランク相関を純粋 Python で実装（ties は平均ランク）。
    - 外部依存（pandas 等）を使わない軽量実装。
  - src/kabusys/research/__init__.py を追加し、研究向け API を再エクスポート（calc_momentum などと zscore_normalize の再エクスポート）。

- Data（データ基盤）モジュール
  - src/kabusys/data/calendar_management.py を追加（JPX カレンダー管理）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日判定ユーティリティを提供。
    - market_calendar テーブルがない／未取得の場合の曜日ベースのフォールバックを採用し、DB 登録値優先の一貫した挙動を実現。
    - calendar_update_job により J-Quants API からの差分取得 → market_calendar への冪等保存を実行。バックフィル・健全性チェック（未来日付閾値）を実装。
    - jquants_client 呼び出し点を分離（jq.fetch_market_calendar / jq.save_market_calendar）。
  - src/kabusys/data/pipeline.py を追加（ETL パイプライン基盤）。
    - ETLResult dataclass を提供（取得件数、保存件数、品質問題リスト、エラーリスト、ユーティリティメソッド to_dict、has_errors, has_quality_errors）。
    - テーブルの最大日付取得やテーブル存在チェックなどの内部ユーティリティを実装。
    - 差分更新・バックフィル・品質チェック方針を設計に反映。
  - src/kabusys/data/etl.py を追加して ETLResult を再エクスポート。
  - src/kabusys/data/__init__.py を追加（パッケージ初期化）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 外部 API（OpenAI / J-Quants）キーは引数注入または環境変数経由で取得し、未設定時は ValueError を発生させ安全に扱うように設計。

Notes / 実装上の注意
- すべての時刻処理でルックアヘッドバイアス防止を重視し、datetime.today()/date.today() の直接参照を避け、target_date を明示的に受け取る設計を採用しています（テスト／バックテストの再現性確保）。
- OpenAI 呼び出しのラッピング関数は各モジュール内に独立して実装しており、モジュール間でプライベート関数を共有しないことで結合度を下げ、テスト時に容易に差し替えられるようにしています。
- DuckDB に対する SQL は互換性や空パラメータの制約（executemany で空リスト不可）を考慮して実装されています。
- ロギングを多用し、フェイルセーフ動作（API 失敗時のスコア 0.0 フォールバック、部分失敗時の DB 保護など）を優先しています。

開発者へのヒント
- テスト時に自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをモックするには各モジュールの _call_openai_api を unittest.mock.patch してください（news_nlp と regime_detector は独立実装のため別々にパッチ可能）。

--- 

（補足）この CHANGELOG は提供されたソースコードから実装内容を推測して作成しています。実際の変更履歴や過去バージョンがある場合は適宜差し替えてください。