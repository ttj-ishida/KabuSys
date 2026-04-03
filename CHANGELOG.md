# Changelog

すべての変更は Keep a Changelog の方針に従います。セマンティックバージョニングを使用します。  

リンクや詳細なコミット履歴はこのリポジトリのソースを参照してください。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージトップでの公開モジュール: data, strategy, execution, monitoring（__all__ にて公開）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動読み込み機能を実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - .env パーサを実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
  - 環境変数読み込み時の上書き制御:
    - override フラグと protected キーセット（既存 OS 環境変数を保護）をサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - J-Quants / kabu ステーション / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL など）をラップ。
    - 必須値取得用の _require() による ValueError 投出。
    - env 値や log_level のバリデーション（許容値チェック）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄単位にニューステキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム設定、タイムウィンドウ（JST基準 → UTCへの変換）を実装。
    - JSON Mode を想定したレスポンスパースと堅牢なバリデーション（余分な前後テキストの復元、results 配列チェック、コード/スコア型チェックなど）。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフでのリトライ実装。その他の失敗はフェイルセーフによりスキップして継続。
    - DuckDB への書き込みは idempotent に DELETE → INSERT（対象コードのみ）することで部分失敗時の保護を実施。
    - テスト容易性のため OpenAI 呼び出し箇所は patch で差し替え可能（kabusys.ai.news_nlp._call_openai_api をモック可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（ウェイト 70%）とマクロニュースの LLM センチメント（ウェイト 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から MA200 乖離を算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - raw_news からマクロ経済キーワードでフィルタしてタイトルを抽出し、OpenAI で macro_sentiment を計算。記事がない場合は LLM 呼び出しをスキップして 0.0 を採用。
    - OpenAI 呼び出しに対するリトライ・エラー処理やレスポンスパースのフェイルセーフを実装。
    - 判定結果は market_regime テーブルにトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に保存。失敗時は ROLLBACK して例外を上位へ伝播。

- データプラットフォーム / ETL (kabusys.data)
  - ETL 結果表現用の ETLResult データクラスを追加（kabusys.data.pipeline.ETLResult を再エクスポート）。
    - 取得件数、保存件数、品質問題、エラー一覧などを保持。品質エラーの有無や辞書化 to_dict をサポート。
  - pipeline モジュール (kabusys.data.pipeline)
    - 差分取得・保存・品質チェックフローの基盤を実装。J-Quants クライアント経由での差分取得と idempotent 保存方針を想定。
    - backfill_days による後出し修正吸収、品質チェックは重大度を持ちながら全件収集して継続する方針を採用。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを前提に営業日判定・前後営業日検索・期間内営業日一覧取得等のユーティリティを実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックするロジックを採用し、DB がまばらな場合でも一貫した振る舞いを保つ。
    - calendar_update_job による J-Quants からの差分取得および保存（バックフィル、健全性チェック、ON CONFLICT 相当の保存を想定）を実装。
    - 探索上限 _MAX_SEARCH_DAYS により無限ループを回避する安全策を実装。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、ma200_dev、ATR（20日）、流動性（20日平均売買代金・出来高比）などの計算関数を追加。
    - DuckDB 上で SQL を用いて効率的に計算し、結果を dict のリストで返す。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）、rank、統計サマリー（count/mean/std/min/max/median）等の実装。
    - 外部依存を増やさない実装（pandas などを使用していない）を採用。

### Changed
- 初回リリースに伴う各モジュールの設計上の決定点を README/ドキュメントに反映（コード内 docstring として詳細な設計方針を記載）。
  - ルックアヘッドバイアス回避のため、すべての「判定日 / スコア日」は明示的な target_date を受け取り、datetime.today()/date.today() に依存しない設計。
  - OpenAI 呼び出しは JSON Mode を想定し、厳密な JSON を期待するプロンプトを採用。余剰テキストに対する復元ロジックも実装。

### Fixed
- 初期実装段階での堅牢性向上:
  - DB 書き込み時にトランザクション／ROLLBACK を明示し、ROLLBACK 失敗時は警告ログを出力して上位へ例外を伝播する安全処理を追加。
  - OpenAI レスポンスのパースエラーや API エラー発生時にフェイルセーフ（スコア=0.0 / スキップ）することで ETL 全体や日次ジョブが停止しないように調整。

### Notes / Known limitations
- OpenAI API キー（OPENAI_API_KEY）が未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する。
- gpt-4o-mini を前提としたプロンプト／JSON Mode を想定しているため、将来的にモデルや SDK が変わる場合は応答パースの変更が必要になる可能性がある。
- DuckDB の executemany に空リストを渡せないバージョン（例: 0.10）の互換性を考慮した処理を実装しているため、DuckDB バージョンによる差異に注意。
- timezones:
  - ニュースウィンドウは JST を基準に定義し、DB 上の日時は UTC naive として比較する前提。運用時は raw_news.datetime のタイムゾーン取り扱いに注意が必要。
- テスト支援:
  - AI 呼び出し部は内部関数をモックして差し替えられる設計（_kabusys.ai.*._call_openai_api を patch）になっているためユニットテストが容易。
- 未実装 / 今後の拡張:
  - strategy / execution / monitoring パッケージはエントリポイントとして公開されているが、実運用に必要な実装や CLI / Scheduler 連携は今後の拡張対象。

---

（補足）
- リリースノートはコードベースの実装内容から推測して作成しています。実際のリリース履歴や追加／削除された機能はリポジトリのコミット履歴やリリース管理情報を参照してください。