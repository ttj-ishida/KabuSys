KEEP A CHANGELOG
全ての変更は慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- なし

[0.1.0] - 2026-03-28
Added
- パッケージ初期リリース。日本株自動売買システムのコア機能を実装。
- パッケージメタ:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開 API に data, strategy, execution, monitoring を想定したエクスポートを追加（strategy/execution/monitoring の実体は今後拡張想定）。
- 環境設定管理 (src/kabusys/config.py):
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどを考慮。
  - OS 環境変数を保護する protected キー指定、override 挙動のサポート。
  - Settings クラスを提供し、必須環境変数取得時の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）とデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を提供。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェック（development / paper_trading / live、DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- AI (src/kabusys/ai):
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大20銘柄／API呼び出し）、1銘柄あたりの最大記事数と最大文字数でトリム。
    - JSON Mode 出力のバリデーションと堅牢なパース（前後余分テキストの復元ロジック含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
    - DuckDB への冪等的書き込み（対象コードのみ DELETE → INSERT）や、部分失敗時の既存データ保護。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事はキーワードフィルタリングで抽出、LLM（gpt-4o-mini）に JSON 出力で評価させ、レスポンスのパース・リトライを実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- データプラットフォーム (src/kabusys/data):
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar に基づく営業日判定 API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）でのフォールバック。
    - カレンダー更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で差分取得・保存し、バックフィル・健全性チェックを含む。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得数／保存数／品質問題／エラーの集計）。
    - 差分更新・backfill・品質チェック（kabusys.data.quality を使用）等の設計方針を実装するベースを提供。
    - _get_max_date 等ユーティリティで DuckDB のテーブル存在チェックや最大日付取得を実装。
- リサーチ（src/kabusys/research）:
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum (1M/3M/6M リターン)、200 日 MA 乖離、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高変化率）、Value（PER, ROE）を DuckDB 上で SQL により計算する関数を実装。
    - データ不足時は None を返す等の堅牢性を確保。
    - 出力は (date, code) ベースの辞書リスト。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応。ホライズン検証（正の整数、最大252）を実施。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。データ不足・ゼロ分散を考慮して None を返す場合あり。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
- 内部設計上の注意点・安全策:
  - ルックアヘッドバイアス防止: 各処理は datetime.today()/date.today() を内部で参照しない（target_date を明示的に受け取る）。
  - DuckDB を主要なストレージ層として利用。
  - OpenAI 呼び出しは各モジュールで独立実装し、テスト時は関数を差し替えやすく設計（unittest.mock.patch を想定）。
  - API エラー時はフェイルセーフ（例: 0.0 フォールバック）や部分失敗の影響を最小化する実装を採用。
  - ロギングを広範に追加し、失敗時は警告/例外情報を出力。

Changed
- 初回公開のため該当なし

Fixed
- 初回公開のため該当なし

Security
- 初回公開のため該当なし

Notes / 今後の拡張予定（暗黙の示唆）
- strategy / execution / monitoring 実体の追加（現在はパッケージ公開名のみ存在）。
- J-Quants クライアントの実装詳細（jquants_client）と品質チェック（quality）モジュールの完全実装／テスト。
- Slack 連携（通知）や実際の売買執行ロジックの実装・検証。
- 単体テスト、統合テスト、CI パイプライン導入。

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートと差異がある場合は適宜調整してください。）