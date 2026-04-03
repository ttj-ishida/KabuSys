Keep a Changelog
=================

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット
----------
各リリースは日付順（新しいものが上）で記載します。カテゴリは主に Added / Changed / Fixed / Security / Deprecated / Removed を使用します。

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース "KabuSys" — 日本株自動売買／リサーチ用ライブラリのコア機能を実装。
- パッケージ公開情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py にて定義）。
  - public サブパッケージ: data, research, ai, （および strategy, execution, monitoring を __all__ に含むが詳細は個別実装に依存）。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイル（.env と .env.local）および OS 環境変数から設定を自動ロード（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export 句、シングル／ダブルクォート、エスケープ、コメント取り扱いに対応。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境モード等のプロパティとバリデーション）。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError を送出）。
- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント ai_score を算出して ai_scores テーブルへ保存。
    - バッチ処理（1 API コールあたり最大 20 銘柄）とチャンク処理、記事トリム（最大記事数、最大文字数）を実装。
    - 再試行ロジック（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の型チェック）を実装。スコアは ±1 にクリップ。
    - DuckDB の executemany の挙動差分に対する保護（空リストを渡さない等）。
    - テスト容易性のため API 呼び出し箇所を patch 可能に設計（_call_openai_api）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動 ETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースはキーワードベースで抽出（日本・米国等のマクロキーワードを用意）。LLM 呼び出しは gpt-4o-mini / JSON Mode、リトライ・フォールバックロジックを実装。API 失敗時は macro_sentiment を 0.0 にフォールバック。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用、datetime.today() を直接参照しない）。
- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 記録がない場合の曜日ベースフォールバック（週末除外）や、DB の一貫性を保つ設計（最大探索日数の制限など）。
    - calendar_update_job: J-Quants API からカレンダーを差分取得して market_calendar に冪等更新。バックフィル（直近日数の再フェッチ）と健全性チェックを実装。
  - pipeline / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー集約など）。
    - 差分取得・バックフィル・品質チェック（quality モジュール想定）を想定したパイプライン設計。
    - jquants_client を利用してデータ取得・保存を行う想定（save_* 系関数呼び出し）。
- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、ATR 比率、出来高指標）、Value（PER, ROE）を DuckDB SQL で計算する関数を実装。データ不足時は None を返す設計。
    - 計算は prices_daily / raw_financials のみ参照し、本番取引 API へアクセスしない。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（スピアマンのランク相関）calc_ic、rank（同順位を平均ランクにする実装）、統計サマリー factor_summary を実装。
    - pandas 等の外部依存を持たず標準ライブラリで実装。
- ロギングとエラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを導入（情報ログ・警告・例外ログ）。
  - DB 書き込み時は BEGIN / DELETE / INSERT / COMMIT の流れで冪等に書き込み、失敗時は ROLLBACK と例外伝播を行う実装。

Changed
- （初回リリースのため過去との互換性変更はなし）

Fixed
- （初回リリースにおける実装上の堅牢化）
  - OpenAI API の異常応答（非 5xx / 5xx / タイムアウト / レート制限）を区別して適切にリトライまたはフォールバックする処理を追加。
  - DuckDB の executemany に空リストを渡すと失敗する点に対するガードを追加（空時は実行しない）。

Notes / Important
- OpenAI API（gpt-4o-mini）を利用する機能は api_key が必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する旨を各関数で明示。
- .env の自動読み込みはパッケージ内からプロジェクトルートを探索して行うため、パッケージ配布後も想定した動作をします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp / regime_detector の OpenAI 呼び出しはテストで差し替え可能に設計（ユニットテストでモックしやすい）。
- DuckDB / Data モジュールは日付処理においてルックアヘッドバイアスを避ける設計（target_date パラメータ駆動、date.today() を使わない等）。

Known issues / Limitations
- 一部 __all__ に含まれるモジュール名（strategy, execution, monitoring 等）はパッケージの公開対象として定義されているが、このリリースではコードスニペットの範囲により詳細実装が見えないため、実装済み機能の範囲は上記に記載したモジュールに準じます。
- 外部 API（J-Quants, OpenAI）に依存するため、実行には各種 API キーとネットワーク接続が必要です。
- DuckDB の日付/リストバインドの互換性はバージョン差に影響される可能性があるため、環境依存の挙動には注意が必要（コード中に互換性保護ロジックあり）。

Contributing
- バグ修正・機能追加は Pull Request を歓迎します。テストしやすさを意識して、外部 API 呼び出し箇所はモック可能な構成を維持してください。

ライセンス
- 本リリースのライセンス情報はリポジトリの LICENSE を参照してください。