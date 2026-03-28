# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはパッケージのコード内容（src/ 以下）から推測して作成した初期リリースの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しています。主な追加点と設計上の特徴は以下のとおりです。

### 追加 (Added)

- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) にバージョン 0.1.0 を設定し主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
  - settings 用の Settings クラス (src/kabusys/config.py) を追加。環境変数から各種設定を取得するプロパティ群を提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。

- 環境変数読み込み
  - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みする仕組みを実装。
  - `.env.local` は `.env` より優先して上書き（override）する設計。OS 環境変数を保護するため protected キー集合を利用。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォートなしの場合の扱い）に対応。

- AI（自然言語処理）関連
  - ニュースセンチメント（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini / JSON mode）でセンチメントを付与して ai_scores テーブルへ保存する処理を実装。
    - API 呼出はバッチ処理（最大 20 銘柄/チャンク）とし、リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。
    - レスポンスの厳密バリデーション、JSON 前後ノイズの復元ロジック、スコアの ±1.0 クリップを実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - タイムウィンドウ計算（JSTベース → DBは UTC 前提）を提供（calc_news_window）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して market_regime テーブルに日次判定を書き込む機能を実装。
    - LLM 呼出は JSON 出力を期待し、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - ルックアヘッドバイアス対策として target_date 未満のデータのみ使用し、datetime.today()/date.today() に依存しない設計。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データ（data）
  - ETL パイプライン（data.pipeline）
    - ETLResult データクラスを追加し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を集約。
    - 差分取得やバックフィル、品質チェック運用を想定したユーティリティ基盤を実装（jquants_client, quality モジュール連携を想定）。
  - カレンダー管理（data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫した方針。
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を行うジョブを実装。健全性チェック（将来日付の異常検出）あり。

- リサーチ（research）
  - ファクター計算（research.factor_research）
    - モメンタム（1M/3M/6M）、200日移動平均乖離、20日 ATR（atr_20）、流動性（平均売買代金・出来高比）等を DuckDB SQL で計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - raw_financials を参照して PER/ROE を算出するバリューファクターを実装。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。pandas 等外部ライブラリに依存しない純標準ライブラリ実装を想定。
  - data.stats に用意された zscore_normalize を再利用可能にエクスポート。

### 変更 (Changed)

- なし（初回リリース）

### 修正 (Fixed)

- 考慮済みの堅牢性向上点（実装に明示）
  - DuckDB に対する executemany の空リストバインドに関する互換性考慮（空時は実行をスキップ）。
  - DB トランザクション失敗時に ROLLBACK を試行し、さらに ROLLBACK が失敗した場合は警告ログを出す設計。
  - OpenAI レスポンスの JSON パース失敗時に前後の余計なテキストを除去して復元を試みるフォールバック処理。
  - news_nlp/regime_detector の API 呼出で発生し得る各種例外（RateLimitError、APIConnectionError、APITimeoutError、APIError）の扱いを明確化し、該当ケースではリトライあるいは安全にフォールバックして処理継続するロジックを導入。
  - 設定値の妥当性チェック（KABUSYS_ENV の許容値チェック、LOG_LEVEL 値チェック）を追加。

### セキュリティ (Security)

- センシティブ情報は環境変数で管理する設計（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
- .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- .env の読み込み実装は OS 環境変数を上書きしない既定動作と、.env.local による安全なオーバーライドをサポート。

### 既知の注意事項 / 制約 (Notes)

- このリポジトリは DuckDB（DuckDBPyConnection）と OpenAI Python SDK（OpenAI クライアント）に依存します。これらの環境が必要です。
- jquants_client モジュール（J-Quants API とのインタフェース）は参照されますが、本 CHANGELOG 作成時点のコード一覧には実装ファイルが含まれていません。実運用では jquants_client の実装と適切な API トークンが必要です。
- OpenAI に対する呼び出しはコストとレート制限が発生します。大量のバッチ実行時は運用ポリシーを検討してください。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提となります。スキーマ準備が必要です。
- LLM を用いた判定はモデルやプロンプト依存です。将来のモデル変更時はプロンプト・レスポンス処理の見直しが必要となる可能性があります。

---

開発・運用に関する詳細な実装意図や設計方針は各モジュールの docstring に記載されています。必要であれば各関数やモジュールごとの詳細な変更点や設計メモを追記します。