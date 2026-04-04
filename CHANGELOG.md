# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
バージョン番号はパッケージの __version__ と一致します。

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買システムのコアモジュール群を追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージの公開 API: ["data", "strategy", "execution", "monitoring"] を __all__ に設定。

- 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export 句、クォート、エスケープ、インラインコメント対応。
    - .env ファイル読み込み失敗時は警告を出力して継続。
  - Settings クラスを実装し、主要設定値（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境等）をプロパティで提供。
    - 必須キー未設定時は明示的に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV の値検証（development / paper_trading / live）および LOG_LEVEL の検証（DEBUG, INFO, ...）。
    - Path を返す設定値は expanduser で展開。

- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - タイムウィンドウ計算関数 calc_news_window（前日 15:00 JST ～ 当日 08:30 JST を UTC ベースで返す）。
    - OpenAI（gpt-4o-mini）へのバッチ送信を実装（最大バッチサイズ 20 銘柄）。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - JSON Mode のレスポンス検証と耐性（前後余計なテキストのトリミング）を実装。
    - スコアは ±1.0 にクリップし、成功分を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（ユニットテストで patch 可能）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースの抽出はマクロキーワードリストに基づき raw_news からタイトルを取得。
    - OpenAI（gpt-4o-mini）で macro_sentiment を評価し、リトライやフェイルセーフ（API 失敗時は 0.0）を実装。
    - レジームスコアを合成して market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - lookahead バイアス回避のため datetime.today() 等を直接参照しない設計（target_date ベース）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダーの夜間バッチ更新 job (calendar_update_job) を実装（J-Quants クライアント経由で差分取得→保存）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日（平日のみ営業）でフォールバックする堅牢なロジック。
    - 最大全探索日数を設定して無限ループ防止、バックフィル・健全性チェックを実装。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.py から再エクスポート）。
    - 差分更新・バックフィル・品質チェック・冪等保存（jquants_client.save_*）を想定した設計。
    - ETLResult は品質問題（quality_issues）やエラー一覧を保持し、has_errors / has_quality_errors プロパティ、辞書化メソッドを提供。
    - 内部ユーティリティで DuckDB テーブル存在チェックや最大日付取得などを実装。

- リサーチ（kabusys.research）
  - ファクター計算 (factor_research.py)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比）
    - バリュー: calc_value（PER, ROE = raw_financials を参照）
    - DuckDB 上の SQL を用いた実装で、データ不足時の None 返却やログ出力を実装。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（任意ホライズンのリターン、ホライズン検証あり）
    - IC 計算: calc_ic（Spearman ランク相関）
    - ランク変換: rank（同順位は平均ランク、丸め処理で ties を安定化）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）

### 変更 (Changed)
- （初回リリースのため変更履歴はなし）

### 修正 (Fixed)
- （初回リリースのため修正履歴はなし）

### 注意点 / 設計上の特徴
- OpenAI API 呼び出しには openai ライブラリを使用（gpt-4o-mini, JSON Mode を利用想定）。API キー未設定時は ValueError を送出する設計。
- DuckDB を主要なローカルデータベースとして利用。SQL と Python を組み合わせた処理で高パフォーマンスを目指す。
- ルックアヘッドバイアス対策として内部実装はいずれも target_date を明示的に受け取り、datetime.today() 等を参照しない方針。
- DB 書き込みは冪等性・トランザクション（BEGIN/COMMIT/ROLLBACK）を考慮。ROLLBACK 失敗時は警告ログを出力。
- API エラーやパース失敗時はフェイルセーフで処理を継続する（多くの場合スキップして 0.0 などのデフォルト値にフォールバック）。
- テストを考慮し、OpenAI 呼び出し部分など差し替え可能な設計（モジュール内プライベート関数を patch してテスト可能）。

---

将来のリリースでは、以下のような追加・改善が想定されます（非包括的）:
- strategy / execution / monitoring 周りの発注ロジック・実行管理の実装・改善
- ai の多言語対応やモデル切替、より強力なバリデーション
- ETL のジョブスケジューリング・監査ログ・可観測性の強化
- テストカバレッジ拡充と CI/CD の統合

この CHANGELOG はコードベースから推測して作成したものであり、将来的な変更や別ブランチの差分は含みません。