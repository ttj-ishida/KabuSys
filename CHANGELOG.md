CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントを定義 (src/kabusys/__init__.py)。
  - public サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境変数 / 設定管理モジュール (src/kabusys/config.py)
  - .env ファイルと環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、__file__ から探索するため CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォートおよびバックスラッシュエスケープ対応）。
  - Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値設定。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を列挙）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュースNLP と LLM ベースの分析 (src/kabusys/ai/)
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) に JSON Mode でバッチ送信して銘柄毎のセンチメントスコアを ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC で比較）。
    - バッチサイズ、記事数・文字数のトリム制御、最大リトライ（429/ネットワーク/5xx）などの堅牢化を実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップを実装。
    - DuckDB の executemany の制約を考慮した部分置換（DELETE → INSERT）で冪等性と部分失敗耐性を確保。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは事前定義キーワードでフィルタし最大件数を制限。
    - API 呼び出しのリトライ・バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない実装方針を採用。
    - OpenAI クライアントは引数経由または環境変数 OPENAI_API_KEY を用いて解決。未設定時は ValueError を送出。

- データ管理モジュール (src/kabusys/data/)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティを追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にデータが無い場合は曜日ベースでフォールバック（週末は非営業日）し、DB がある場合は DB 値を優先、未登録日は一貫した曜日フォールバックを採用。
    - calendar_update_job: jquants_client を用いて差分取得・バックフィル・健全性チェックを行い market_calendar を更新。
    - 探索上限 (_MAX_SEARCH_DAYS) を設定し無限ループを防止。
  - pipeline / etl:
    - ETLResult dataclass を導入し、ETL 実行結果（取得件数、保存件数、品質問題、エラー一覧等）を体系化して返却可能に。
    - 差分更新、バックフィル、品質チェックの設計方針を反映したユーティリティ実装（詳細は pipeline モジュール内）。
    - DuckDB テーブル存在チェック・最大日付取得等の補助関数を提供。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily, raw_financials を参照してモメンタム、ATR、流動性、PER、ROE 等を計算。
    - データ不足や条件付きで None を返す設計（例: MA200 に 200 行未満なら ma200_dev は None）。
    - DuckDB のウィンドウ関数を活用した実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンパラメータ検証あり。
    - calc_ic: スピアマン（ランク）相関を計算し、データ不足時は None を返す。
    - rank: 同順位は平均ランクで扱うランキング実装。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージのエクスポートを整備（代表的な関数を __all__ で公開）。

Changed
- none（初期リリースのため該当なし）

Fixed
- none（初期リリースのため該当なし）

Security
- none（現時点で公開のセキュリティ修正はなし）

Notes / Implementation details / 備考
- OpenAI（gpt-4o-mini）呼び出しまわり
  - JSON Mode を利用し厳密な JSON 出力を期待する実装。ただし API レスポンスに余分なテキストが混入するケースを考慮して復元ロジックや堅牢なパース処理を用意。
  - リトライ戦略は 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフを実施。その他エラーはフォールバックやスキップ処理を行う（例外を上位に伝播させない箇所あり）。
  - テスト容易性を考慮して内部の _call_openai_api 関数を unittest.mock.patch で差し替え可能にしている。
- DuckDB 特有の互換性考慮
  - executemany に空リストを渡せないバージョンへの対応（条件判定で空チェックを行う）。
  - SQL 内で日付型が文字列で返る場合を想定した変換処理を実装。
- ルックアヘッドバイアス対策
  - 多くの分析/スコアリング関数が datetime.today() / date.today() を直接参照せず、外部から target_date を受け取る設計。
- 環境変数の扱い
  - 必須値が未設定の場合は明示的な ValueError を投げる設計（運用時に設定ミスを早期検出）。
  - 自動ロードの有無を制御するフラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を提供。
- 部分失敗耐性
  - ai_scores や market_regime への書き込みは対象コードに絞って置換（DELETE → INSERT）し、部分的な API 障害が既存データを全消去しないよう工夫。

Breaking Changes（互換性の壊れる変更）
- 初期リリースにつき該当なし。

今後の予定（想定）
- 監視 / 実行戦略の実装強化（strategy, execution, monitoring パッケージの実装拡張）。
- ai モデルの選択肢追加、評価・キャリブレーション機能の充実。
- jquants_client の実装詳細に依存する ETL の堅牢化と品質チェック機能の拡張。

お問い合わせ / 貢献
- バグ報告や機能追加の提案は issue を立ててください。開発方針やテストカバレッジに関する議論も歓迎します。