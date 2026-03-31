CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠します。
詳細: https://keepachangelog.com/ja/1.0.0/

注意:
- 日付はコードベースの最初の公開バージョンとして 2026-03-31 を使用しています（ソースから推測）。
- 実装上の設計方針や既知の制約も併せて記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順: OS 環境 > .env.local > .env）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサは export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理に対応。
  - OS 環境変数保護機能（protected set） により既存の環境変数を誤って上書きしない。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV の既定値と検証を実装。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルのニュースを集約し、銘柄毎に OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較、calc_news_window 関数を提供）。
    - バッチ処理: 1 API コールあたり最大 20 銘柄（_BATCH_SIZE=20）。
    - 1 銘柄あたり最大記事数 10 件、テキストは最大 3000 文字にトリム（トークン対策）。
    - JSON レスポンスのバリデーションとスコアクリップ（±1.0）。
    - リトライと指数バックオフ（429、ネットワーク断、タイムアウト、5xxを対象、最大リトライ回数 3）。
    - API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。
    - DuckDB への書き込みは部分失敗時に既存データを保護するため、対象コードに対して DELETE → INSERT の置換を行う（トランザクション管理）。
    - テスト容易性のため _call_openai_api は独立実装でモック差し替え可能。
    - 出力関数: score_news(conn, target_date, api_key=None) を公開（戻り値: 書込銘柄数）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）と、ニュースベースの LLM マクロセンチメント（重み 30%）を合成してレジーム（bull / neutral / bear）を日次判定。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドを排除。
    - マクロニュースは news_nlp の calc_news_window と raw_news を用いて取得（マクロのキーワードリストは実装内に定義）。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用、失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - レジームスコアはクリップしてラベル付与し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しの再試行・5xx 判定、ログ出力などの堅牢性対策を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)（戻り値: 1=成功）。

- データ関連モジュール（src/kabusys/data）
  - ETL・パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを定義しパブリックに再エクスポート（kabusys.data.ETLResult）。
    - 市場データの差分取得、保存（jquants_client を通す）、品質チェック（quality モジュール）を想定した設計。
    - 最終取得日のバックフィル、エラーハンドリング、品質問題の収集方式を実装方針として明記。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティなどを提供。
    - ETLResult.to_dict() で品質問題をシリアライズ可能。

  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルをベースに営業日判定ロジックを提供:
      - is_trading_day(conn, date)
      - is_sq_day(conn, date)
      - next_trading_day(conn, date)
      - prev_trading_day(conn, date)
      - get_trading_days(conn, start, end)
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバック。
    - next/prev/get_trading_days は DB 値優先、未登録日は曜日フォールバックで一貫した結果を返す実装。
    - カレンダー夜間バッチ: calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得 → jq.save_market_calendar による冪等保存。
      - バックフィル（直近 _BACKFILL_DAYS 再取得）、健全性チェック（過度な将来日付はスキップ）を実装。

- リサーチモジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）。
    - Value: latest raw_financials（report_date <= target_date）を用いた PER（EPS が 0/欠損時は None）と ROE。
    - DuckDB を主体とした SQL 実装。出力は list[dict] 形式（date, code を含む）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）
    - IC 計算（Spearman の ρ）: calc_ic(factor_records, forward_records, factor_col, return_col)
    - ランク変換ユーティリティ: rank(values)
    - ファクター統計サマリー: factor_summary(records, columns)
    - pandas 等の外部ライブラリに依存しない純 Python 実装を採用。

- テスト性・互換性配慮
  - OpenAI 呼び出し部分（news_nlp/_call_openai_api, regime_detector/_call_openai_api）は差し替えやすく、ユニットテストでモック可能。
  - DuckDB executemany の挙動差異（空リスト不可）を考慮して空チェックを実装。

Fixed
- .env パースの空行・コメント・export プレフィックスの扱い、およびクォート内のエスケープ処理を明確化。これにより .env の柔軟な記載に対応。

Security
- OS 環境変数が .env で上書きされないよう protected set を使用して保護。
- API キー（OpenAI）は引数注入と環境変数の両方をサポートし、未設定時に明示的な ValueError を発生させる。

Known issues / Notes / Limitations
- OpenAI のレスポンス形式に強く依存（JSON mode を想定）。モデルや API の挙動変化があるとパースや検証処理の調整が必要。
- news_nlp と regime_detector は gpt-4o-mini を使用する実装になっているため、モデル変更時は _MODEL 定数を更新し、出力フォーマット（JSON）を維持する必要あり。
- DuckDB バインドや executemany の挙動はバージョン差で影響を受ける（空リストによる問題等）。既知の互換性対策はコード内にコメント済み。
- リサーチ機能は pandas 等を使わない軽量実装。大規模データや高度な統計処理には追加最適化が必要。
- ETL の jquants_client / quality モジュールの具体的実装はこのコードスニペットからは外部依存（呼び出しインターフェースは仮定）になっています。

リリースノートの参考（開発者向け）
- 自動.envロードをオフにするテストを書く場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 呼び出しをユニットテストでモックする場合は各モジュールの _call_openai_api を patch する。
- DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を保っているため、部分失敗のハンドリングは安全に行われます。

追記（将来の改善案）
- レスポンス検証の更なる堅牢化（スキーマ検証ライブラリの導入検討）。
- ニュースのトークン数・コンテキスト長に応じた動的バッチサイズ調整。
- OpenAI API のメトリクス収集／監視（レイテンシ・エラー率）機能追加。
- pandas 等を optional 依存として追加し、リサーチ処理の高速化オプションを提供。