Changelog
=========
すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠し、SemVer を想定しています。

[Unreleased]: https://example.com/kabusys/compare/0.1.0...HEAD
[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース。モジュール群を追加。
  - kabusys.__init__.py
    - パッケージのバージョンを "0.1.0" として公開。
    - public API として data, strategy, execution, monitoring をエクスポート。
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
    - 自動 .env ロード機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - .env と .env.local の読み込み順序制御（OS 環境変数保護機能付き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止対応。
    - 必須環境変数検査用の _require ユーティリティと、env/log_level の妥当性検証（development/paper_trading/live、DEBUG/INFO/...）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）、Slack / kabu / J-Quants 用設定のプロパティを提供。
  - kabusys.ai
    - news_nlp モジュール（score_news）: raw_news を OpenAI (gpt-4o-mini) に投げて銘柄別センチメントを ai_scores に保存する処理を実装。
      - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（calc_news_window）。
      - 記事集約、文字数/記事数トリム、バッチ（最大20銘柄）での API 呼び出し。
      - JSON Mode を期待したレスポンスのバリデーションとスコアクリップ（±1.0）。
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時は安全にスキップ。
      - テスト用に _call_openai_api を patch 可能（unittest.mock.patch 想定）。
    - regime_detector モジュール（score_regime）: ETF(1321) の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う。
      - MA 計算、マクロ記事抽出（キーワードベース）、OpenAI 呼び出し・リトライ処理、スコア合成、DB トランザクション処理を実装。
      - API 失敗やレスポンスパース失敗は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
      - news_nlp と意図的に内部実装を分離（モジュール結合を避ける設計）。
  - kabusys.data
    - calendar_management モジュール:
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ群を実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar の無い場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
      - calendar_update_job: J-Quants から差分取得 → 冪等保存（ON CONFLICT/上書き）を行う夜間バッチジョブを実装。バックフィル、健全性チェックを組み込み。
    - pipeline / etl モジュール:
      - ETLResult データクラスを公開（etl から再エクスポート）。
      - pipeline モジュールは差分更新、idempotent 保存（jquants_client 経由）、品質チェック（quality モジュール）統合のインターフェースを提供。
      - テーブル最大日付取得ユーティリティ、テーブル存在チェック等の内部ユーティリティを実装。
  - kabusys.research
    - factor_research モジュール:
      - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR）および流動性指標、バリュー（PER, ROE）計算関数を実装。
      - DuckDB を用いた SQL ベースの計算を採用し、外部 API へのアクセスは行わない。
      - 結果を (date, code) をキーとした dict のリストで返す設計。
    - feature_exploration モジュール:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、factor_summary（統計量）を実装。
      - Spearman（ランク相関）実装、同順位の平均ランク処理、欠損/非有限値の扱い、最小有効レコード数判定を実装。
  - いくつかの __init__.py を通じて API を整理して再エクスポート（ai, research, data.etl など）。

Changed
- 設計／実装上の方針を明文化して導入（リリース時点の設計仕様としてドキュメント化）。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をアルゴリズム内部で参照しない設計に統一。
  - DuckDB を主要なローカル分析 DB として利用。executemany の空リスト制約や日付型取り扱いを考慮した実装。
  - OpenAI 呼び出しにおける JSON Mode の利用、レスポンスの頑健なパースと検証（余計な前後テキストの復元ロジック等）。
  - DB 書き込みは冪等性を確保（DELETE→INSERT の置換、トランザクション制御、ROLLBACK 保護を実装）。
  - .env の読み込み順序・保護キーの取り扱い仕様を明確化（OS 環境変数が保護される）。

Fixed
- （初期リリースのため既知のバグ修正履歴なし。ただし各モジュールで失敗時の安全なフォールバックや詳細ログ出力を多用して堅牢性を高めている。）

Security
- OpenAI API キーや外部サービスの認証情報は環境変数経由で取得。Settings クラスは必須値未設定時に ValueError を発生させることで安全な起動を促す。
- .env 読み込みはデフォルトで自動だが、KABUSYS_DISABLE_AUTO_ENV_LOAD で明示的に無効化可能（テスト用の安全策）。

Notes / Implementation details
- OpenAI 呼び出し関数（_kabusys.ai.*._call_openai_api）はテスト時にモック差し替え可能なように分離してある。
- AI モジュールは API エラー（レート制限・ネットワーク断・タイムアウト・サーバー5xx）に対してリトライ戦略を持ち、最終失敗時はスコアを 0.0（中立）にフォールバックする等のフェイルセーフを採用。
- calendar_update_job や ETL 周りは J-Quants クライアント（jquants_client）との連携を前提としており、API 例外時はエラーを記録して処理を継続する設計。
- DuckDB の日付型取り扱いや executemany の空パラメータ制約など、実運用での互換性を考慮した実装上の注意点がコード内に多数コメントされている。

Deprecated
- なし

Removed
- なし

Acknowledgements / References
- 各モジュール内の docstring に DataPlatform.md / StrategyModel.md 等の設計参照が記載されています。実運用ドキュメントと合わせて参照してください。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡張（本リリースではパッケージ名でエクスポートのみ）。
- 単体テスト・統合テストの追加と CI/CD パイプライン整備。
- OpenAI のレスポンス仕様変化に対する互換性レイヤー強化。