# Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]
- 現在未リリースの変更点はありません。

## [0.1.0] - 2026-04-04
初回リリース。本バージョンでは日本株向け自動売買／データ基盤・研究用ユーティリティ群の基礎機能を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（__version__ = 0.1.0、__all__ に data / strategy / execution / monitoring を追加）。
- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）を実装。
  - .env の構文解析を強化（export プレフィックス、シングル・ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - .env 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応。
  - 必須値取得時に未設定だと ValueError を投げる _require() を提供。
  - 主要設定プロパティを公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, OPENAI_API_KEY の想定、データベースパス、監視用 PID/KILL フラグ、閾値、環境/ログレベル判定など）。
- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング: score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を銘柄単位で集約し、OpenAI（gpt-4o-mini、JSON mode）にバッチ送信して ai_scores テーブルへ書き込む。
    - ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチサイズ、トリム（文字数・記事数）とレスポンスバリデーション、±1.0 クリップ、部分書き換えによる冪等保存（DELETE → INSERT）を実装。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライを実装。API失敗時はそのチャンクをスキップして継続するフェイルセーフ設計。
  - 市場レジーム判定: score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタ、OpenAI 呼び出しは独立実装。API失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - ルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ利用、datetime.today()/date.today() をスコープに直接参照しない）。
- データ基盤ユーティリティ (kabusys.data)
  - マーケットカレンダー管理（calendar_management）
    - market_calendar の有無に応じた営業日判定（is_trading_day、is_sq_day）／翌営業日・前営業日計算（next_trading_day、prev_trading_day）／期間内営業日取得（get_trading_days）を実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫性のあるロジックを採用。
    - calendar_update_job により J-Quants から差分取得して冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
    - 異常検知やバックフィル、最大探索日数制限（無限ループ防止）など安全措置を実装。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーリスト等を含む）。kabusys.data.etl で ETLResult を再エクスポート。
    - 差分取得・バックフィル・品質チェック連携を想定した基盤コード（jq クライアント・quality モジュールとの協調）。
    - テーブル存在チェック、最大日付取得などユーティリティを実装（DuckDB 前提）。
- 研究用ユーティリティ (kabusys.research)
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 偏差などを prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取り出し PER / ROE を計算（価格は prices_daily と結合）。
    - 各関数はデータ不足に対する None 戻りやログを適切に処理。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。horizons 検証を実装。
    - calc_ic: スピアマン（ランク）相関による IC 計算（欠損・同順位対応）。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（丸めで ties の誤検出を回避）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。外部ライブラリへ依存せず純粋 Python 実装。
  - 研究モジュールは外部発注 API を呼ばず、DuckDB の prices_daily / raw_financials を参照する設計。
- 共通設計上の注意点・安全策
  - ルックアヘッドバイアス排除（target_date ベースのクエリ、datetime.today() を直接参照しない）。
  - OpenAI API 呼び出しは JSON mode を利用し、レスポンスのバリデーションを行う。
  - DB 書き込みは冪等操作（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を基本とし、ROLLBACK 失敗時もログ出力して上位へ例外を伝播。
  - DuckDB の executemany 空リスト制約等の互換性問題に配慮した実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーなどの機密情報は環境変数経由で取得する設計を採用。自動 .env ロード時も既存 OS 環境変数を保護する仕組み（protected set）を実装。

## 注意事項 / 移行・利用メモ
- OpenAI 連携機能を利用するには OPENAI_API_KEY を環境変数または各関数の api_key 引数で指定してください。未設定時は ValueError が発生します。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。CI/テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 期待される DuckDB テーブル（主なもの）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。関数はこれらのスキーマ前提で動作します。
- API 呼び出し失敗時は部分的に処理をスキップして継続する設計（フェイルセーフ）です。エラーの詳細はログで確認してください。
- 本バージョンでは外部ライブラリ（pandas 等）に依存しない実装を目指しています。大規模データ処理や高頻度更新にあたっては追加の最適化を検討してください。

---

（この CHANGELOG はリポジトリ内の現行コード構造と docstring / 実装から推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース日付・変更差分を正確に反映してください。）