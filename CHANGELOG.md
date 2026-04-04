CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" のガイドラインに準拠しています。

履歴
----

### [0.1.0] - 2026-04-04

Added
- 基本パッケージ
  - パッケージの初期バージョンを追加。src/kabusys/__init__.py でバージョンを "0.1.0" と定義し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定自動読み込みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない動作。
  - .env パーサー（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等）を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 既存の OS 環境変数を保護するため protected set を導入し、.env.local は override=True で上書きが可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル等のプロパティを定義。必須項目が未設定の場合は ValueError を発生させる（_require）。
  - KABUSYS_ENV と LOG_LEVEL の列挙チェックを実装し、不正値に対して明示的な例外を返す。
  - Path 型のプロパティは expanduser を行ってユーザフレンドリーに。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news を実装：raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）の JSON モードを用いて銘柄ごとのセンチメント（ai_scores）を生成・書き込み。
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1銘柄あたり最大記事数・最大文字数でトリムし、最大 _BATCH_SIZE（20）銘柄ずつバッチ送信。
    - 429 / ネットワーク切断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップしてフェイルセーフで継続。
    - レスポンスの厳格なバリデーション実装（JSON 抽出、"results" 構造、コード照合、数値検査、スコアクリップ）。
    - DuckDB に対する冪等書き込み（対象コードのみ DELETE → INSERT）と DuckDB executemany の互換性ワークアラウンド（空リストチェック）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

  - regime_detector.score_regime を実装：ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定・market_regime に保存。
    - MA200 乖離は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタして取得。記事が存在する場合のみ OpenAI を呼び出し、JSON レスポンスから macro_sentiment を取得。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアはクリップされ、閾値に基づきラベルを決定。DB への書き込みは冪等に実行（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK を試みる）。
    - OpenAI 呼び出し実装は news_nlp の内部実装と独立させモジュール結合を抑制。

- Data モジュール（kabusys.data）
  - calendar_management:
    - market_calendar を基にした営業日判定ユーティリティ群を実装（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB にデータがない場合は曜日ベース（平日）をフォールバックとして使用する一貫した設計。
    - calendar_update_job を実装：J-Quants API から差分取得して market_calendar に冪等保存（バックフィル・健全性チェック含む）。jquants_client 経由の fetch/save を利用。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル・先読みのパラメータ化。

  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL 実行結果の構造化（取得数・保存数・品質チェック・エラー一覧）。
    - ETL パイプライン設計（差分更新、idempotent 保存、品質チェック、backfill）に対応するユーティリティ骨子を実装。
    - テーブル存在確認や最大日付取得等の内部ユーティリティを備える。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時の None 処理。
    - calc_volatility: 20日 ATR・ATR 比率・20日平均売買代金・出来高比率を計算。true_range の NULL 伝播を制御し正確なカウントを行う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損時は None）と ROE を計算。
    - 全関数は DuckDB 接続を受け取り、外部 API へアクセスしない設計。

  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を1クエリで取得。horizons の検証（正の整数かつ <=252）実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。最小有効レコード数チェック（>=3）。
    - rank / factor_summary: ランキング（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存を避け、純粋 Python + DuckDB SQL で実装。

Changed
- 設計方針（ドキュメント部分）
  - ほとんどの分析・スコアリング関数は datetime.today()/date.today() を直接参照しない設計とし、外部から target_date を注入することでルックアヘッドバイアスを防止する点を明確化。

Fixed
- N/A（初期リリース）

Security / Notes
- OpenAI API を利用する機能は API キーが必須（引数または環境変数 OPENAI_API_KEY）。キー未設定時は ValueError を送出する明示的な挙動。
- OpenAI へのリクエストは gpt-4o-mini を想定し、JSON mode を使用して厳格な構造を期待する実装だが、API レスポンスの不備に対してはパース耐性（部分 JSON 抽出）とフェイルセーフを備えています。
- データベース書き込みは冪等操作を意識（対象限定 DELETE → INSERT）しており、部分失敗時に既存データを不用意に消さない工夫あり。
- DuckDB のバージョン差異（executemany の空リスト制約など）を考慮した互換性対応が含まれる。

今後
- strategy / execution / monitoring の各パッケージの具現化（発注・実行ロジック、監視エージェント等）。
- ai モジュールの評価・チューニング、モデル・プロンプトの改善。
- ETL の実行本体・スケジューリング、品質チェックの詳細化とアラート機構の実装。

ライセンスや貢献方法などは別途リポジトリの README を参照してください。