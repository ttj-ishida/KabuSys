# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

リリース日付はコードベースの参照日（本ファイル生成日）を使用しています。

## [Unreleased]
（現時点のコードは初回リリース相当の内容のため、Unreleased は空です）

---

## [0.1.0] - 2026-03-29
初回リリース — 基本的なデータパイプライン、研究用ファクター算出、AIベースのニュース解析・市場レジーム判定、カレンダー管理、設定処理などのコア機能を実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェースの定義（__all__）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を基点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化をサポート（テスト用途）。
  - .env のパース実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得・検証。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値検証を実装。
    - path 設定（DUCKDB_PATH、SQLITE_PATH）は Path オブジェクトとして提供。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウの計算（JST 基準）: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime）。
    - バッチ処理（1 API コールにつき最大 20 銘柄）と、1 銘柄あたりの最大記事数／文字数制限によるトークン制御。
    - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対する指数バックオフと最大リトライ回数制御。
    - レスポンス検証: JSON 抽出、results キーの存在、個々の code/score 検証、スコアクリップ（±1.0）。
    - フェイルセーフ: API 失敗やパース失敗時は対象銘柄をスキップして処理継続。
    - テスト容易性のため _call_openai_api をモック可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込む機能を実装。
    - MA200 乖離は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。
    - マクロ記事抽出はマクロキーワード群によるフィルタ（最大 20 記事）。
    - OpenAI 呼び出しは独立実装、API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）および例外時の ROLLBACK 対応。

- 研究（research）モジュール（kabusys.research）
  - factor_research
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時は None。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算する calc_volatility を実装。データ不足は None。
    - Value: raw_financials から取得した直近財務データと株価を組み合わせて PER / ROE を算出する calc_value を実装。
    - 全関数は DuckDB 接続（prices_daily / raw_financials）を受け取り SQL 実行で高効率に計算（外部 API には依存しない）。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1, 5, 21]）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、有効レコード 3 件未満は None）。
    - rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による基本統計量算出（count/mean/std/min/max/median）。
    - pandas 等外部ライブラリに依存しない純 Python 実装。

- データ（data）モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定・次前営業日検索・期間内営業日取得・SQ 日判定 API を実装。
    - DB にカレンダー情報がない場合は曜日ベース（土日休業）でフォールバック。
    - next_trading_day / prev_trading_day は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した振る舞いを提供。探索上限を設定して無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得→保存（バックフィルを含む）を実行。健全性チェックとログ出力あり。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラーの集約）。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を組み合わせる方針を説明する実装骨子。
    - DuckDB 存在チェックや最大日付取得ユーティリティを実装。
  - etl で ETLResult を再エクスポート。

- duckdb を前提にした DB 操作
  - DuckDB 接続を引数に取り、SQL で多数の集計/ウィンドウ関数を利用する設計。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）および executemany の互換性対応（空リスト回避）を考慮。

- 設計方針・品質
  - すべての分析/スコアリング関数は datetime.today()/date.today() を内部参照しない設計（ルックアヘッドバイアス防止）。
  - OpenAI / ネットワーク障害に対してフェイルセーフ（ゼロやスキップで継続）する方針を採用。
  - テスト容易性のため一部内部 API 呼び出しをモック差し替え可能に実装（例: _call_openai_api）。

### Changed
- 初回リリースのため、過去の変更はありません（初期実装）。

### Fixed
- 初回リリースのため、過去の修正項目はありません。

### Known limitations / Notes
- OpenAI API キー（OPENAI_API_KEY）を未設定の場合、score_news / score_regime は ValueError を送出します。テスト時は api_key 引数で明示的に注入可能。
- news_nlp・regime_detector は gpt-4o-mini の JSON Mode を前提としたレスポンス構造を期待します。実運用ではモデルのレスポンス形式に注意が必要です。
- DuckDB のバージョン差異によりリスト型バインドや executemany の挙動に差が出る可能性があるため、互換性処理を実装しています（空リストの executemany 回避等）。
- calendar_update_job は jquants_client（kabusys.data.jquants_client）に依存します。API 呼び出し実装次第で動作が左右されます。
- 初期バージョンのため、追加の監視、メトリクス、エンドツーエンドテスト、ドキュメントの拡充が今後の課題です。

---

今後の予定（例）
- AI スコアリングの拡張（モデル差し替え、詳細なプロンプト管理、キャリブレーションツール）
- ETL の逐次実行やジョブスケジューラ連携、監視・アラートの追加
- 研究モジュールの高速化とオンライン評価基盤構築

（以上）