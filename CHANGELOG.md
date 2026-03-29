# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新の変更は一番上に記載します。

## [Unreleased]
（現在のリリース履歴は以下参照）

---

## [0.1.0] - 2026-03-29

初期公開リリース。日本株向け自動売買／リサーチプラットフォームの基盤機能を実装しています。主な追加点、設計方針、フェイルセーフ／互換性対応を含みます。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージの公開モジュール群（data, research, ai, monitoring, strategy, execution など）の骨組みを準備。

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 環境変数読み取りと必須チェック用の Settings クラスを追加。
  - .env パーサを独自実装：コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 自動ロード無効化のためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを提供（J-Quants, kabuステーション, Slack, DBパス, 環境判定, ログレベル 等）。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事をまとめて LLM（gpt-4o-mini）で銘柄ごとにセンチメントスコア化し、ai_scores テーブルへ書き込む機能を追加。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当）と記事集約ロジックを実装。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数トリム）、JSON Mode レスポンス検証を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。失敗時は部分的にスキップして継続するフェイルセーフ設計。
    - レスポンス検証で結果の型・未知コード・数値性をチェックし ±1.0 にクリップして保存。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - regime_detector: ETF（1321）200日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news をフィルタして記事タイトルを収集、LLM によりマクロセンチメントを取得。
    - API 呼び出しは専用の内部関数で実装、最大リトライ、失敗時は macro_sentiment=0 のフォールバック。
    - レジームスコアの合成、ラベル付け、market_regime テーブルへの冪等（BEGIN / DELETE / INSERT / COMMIT）書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Data（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーの夜間差分取得バッチ（calendar_update_job）と market_calendar を元にした営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を追加。
    - DB 登録がない場合は曜日ベースのフォールバックを行い、一貫した挙動を保つ設計。
    - 最大探索日数制限、バックフィル、健全性チェックなど運用上の安全機構を実装。

  - ETL パイプライン（pipeline）:
    - ETL の実行結果を表す ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分更新、backfill の方針、品質チェック（quality モジュール連携）のための設計を明示。
    - DuckDB 上での最大日付取得やテーブル存在確認ユーティリティを提供。

- Research（kabusys.research）
  - ファクター計算群を追加:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を算出（データ不足時は None を返す）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などボラティリティ・流動性指標を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS が 0/欠損のときは None）。
  - 特徴量探索ツール:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 基本統計（count, mean, std, min, max, median）を算出。
    - rank: 同順位平均ランクを含むランク化ユーティリティ。
  - 実装方針として外部依存（pandas 等）を避け、DuckDB + 標準ライブラリで完結する設計。

### Changed
- （初回リリースのため過去変更点なし。実装時に下記設計選択を反映）
  - 全体を通して「ルックアヘッドバイアス防止」の方針を採用：
    - datetime.today() / date.today() をスコアリング・解析内部で直接参照しない。すべて target_date ベースで処理。
    - prices_daily 等のクエリでは target_date 未満（排他）条件を使用する箇所を明示。
  - DuckDB の互換性に配慮した実装：
    - executemany 前にパラメータが空でないことを確認（DuckDB 0.10 の制約回避）。
    - list 型バインドの不安定さを避けるため個別 DELETE を利用する等の実装。

### Fixed / Safety improvements
- OpenAI API 呼び出し周辺での堅牢性向上:
  - JSON パース失敗や API の一時的障害に対するリトライ／フォールバック処理を追加（429、ネットワーク断、タイムアウト、5xx を考慮）。
  - レスポンスパース失敗時は例外を上位に伝えず、警告ログを出して処理を継続（フェイルセーフ）。ただし DB 書き込み時の例外はロールバックして上位に伝搬。
  - レスポンスの余分な前後テキストの復元（最外の {} を抽出）などの耐性を実装。

- DB 書き込みの原子的設計:
  - market_regime / ai_scores などへの書き込みは明示的なトランザクション（BEGIN / DELETE / INSERT / COMMIT）を用い、例外時は ROLLBACK を試行して状態を保護。
  - ROLLBACK 自体の失敗は警告ログに記録。

### Notes / Operational
- 環境変数:
  - 必須の環境変数が未設定の場合は ValueError を送出する（OpenAI API キー、Slack トークン等）。
  - デフォルト値やファイルパス（例: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV 等）を用意。
  - LOG_LEVEL と KABUSYS_ENV の値検証を実行（許容値以外はエラー）。

- ロギング:
  - 各モジュールに詳細なログメッセージを埋め込み、運用時のトラブルシュートを支援。

- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数を通すことで unittest.mock.patch によるモック差し替えを容易にしている。

---

このリリースはライブラリのコア機能（設定管理、ETL/カレンダー、AI スコアリング、ファクター算出）を一通り揃えた初期版です。運用や拡張に備え、API キーや DuckDB のデータ整備、market_calendar・raw_news・prices_daily 等のテーブル準備が必要です。

今後の予定（例）:
- モデルのプロンプト調整や追加の検証ルール強化
- 監視・モニタリング用のメトリクス出力
- 追加のファクターやポートフォリオ生成ロジックの実装
- 単体テスト・統合テストの整備（現状はモック差し替えを想定した設計済み）