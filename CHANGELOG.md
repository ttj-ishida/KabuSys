Keep a Changelog
=================
すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」規約に従います。  
<https://keepachangelog.com/ja/1.0.0/>

フォーマットの説明
------------------
- Unreleased: 現在開発中の変更（本リリースでは空または無し）
- 各バージョンはリリース日を付記
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用

Unreleased
----------
（なし）

[0.1.0] - 2026-04-03
--------------------
初回公開リリース。以下の主要機能・実装方針を含みます。

Added
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。
  - パッケージ外部公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - 環境変数のパース機能を実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途を考慮）。
  - 環境設定のラッパークラス Settings を提供。J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / 実行環境などをプロパティで取得。
  - 必須変数未設定時は明確な例外（ValueError）を送出する _require 実装。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を参照し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出。
  - タイムウィンドウ計算（JST 基準 → UTC 変換）を実装（前日 15:00 JST 〜 当日 08:30 JST）。
  - バッチ処理（最大 20 銘柄／API コール）・1銘柄あたりの記事数上限・文字数トリムを実装。
  - JSON Mode を利用した応答処理と堅牢なレスポンス検証ロジック（JSON 抽出、results 構造チェック、コード/スコアの検証、スコアの ±1.0 クリップ）。
  - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフのリトライ実装。
  - 部分成功に備えた安全な DB 書き込み（DELETE→INSERT、対象コード絞り込み）と DuckDB の executemany 空リスト制約への対策。
  - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
  - マクロニュース抽出（キーワードリスト）と OpenAI 呼び出しによる macro_sentiment 評価を実装。
  - API 障害時のフォールバック（macro_sentiment = 0.0）を採用してフェイルセーフ化。
  - ルックアヘッドバイアス防止の設計（date.today()/datetime.today() を直接参照せず、prices_daily クエリで target_date 未満のデータのみ使用）。
  - idempotent な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）を実装。
  - OpenAI 呼び出しのリトライ/エラー処理を実装（RateLimit・接続エラー・APIError 等の扱いを明確化）。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末は非営業日）を実装。
    - calendar_update_job による J-Quants からの差分取得 / バックフィル / 健全性チェック（未来日チェック）を実装。
    - DB の値を優先し、未登録日は一貫したフォールバックで補完する設計。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー情報を保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定したインターフェースを用意。
    - _table_exists / _get_max_date 等のユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター群（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB による SQL ベースの実装で、外部 API にはアクセスしない設計。
    - データ不足時に None を返す挙動を明示。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas など外部ライブラリに依存せず、標準ライブラリと DuckDB のみで実装。
  - 研究ユーティリティの公開（__all__ に必要関数を列挙）。

Changed
- 設計方針の明確化（プロジェクト全体）
  - ルックアヘッドバイアス防止（日時の直接参照を避ける）を徹底。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 等を想定）。
  - OpenAI API 周りはリトライ・フォールバック・レスポンス検証を厳格化。

Fixed
- （本バージョンは初期公開のため「既知のバグ修正」は無し。ただし多くの堅牢化処理（NULL/空リスト/例外ハンドリング）を実装して運用上の不具合を低減。）

Security
- 環境変数の必須チェックを導入（未設定時は ValueError）。APIキーの明示的注入をサポートしテストを容易に。
- OS 環境変数を保護するため .env 読み込み時に既存キーを保護するロジックを実装（protected セット）。

Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を使用（gpt-4o-mini を想定）。API 呼び出しは JSON Mode を利用して厳密な構造を期待。
- DuckDB を主要な分析 DB として使用。executemany の空リスト制約など DuckDB の仕様差分に配慮した実装。
- テスト容易性を考慮し、外部呼び出し（OpenAI など）を差し替え可能な構造を採用。
- 日時はすべて date/datetime オブジェクトで扱い、timezone 混入を避ける設計。

Deprecated
- なし

Removed
- なし

今後の予定（参考）
- strategy / execution / monitoring の詳細実装（公開インターフェースは現行で宣言済み）。
- テストカバレッジ拡充、CI ワークフロー追加、ドキュメント（Usage / API）整備。
- J-Quants / kabu API 用のクライアント周りの拡張と例外ハンドリング強化。

Acknowledgements
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。動作・仕様の正式な変更履歴はリリース手続きに合わせて更新してください。