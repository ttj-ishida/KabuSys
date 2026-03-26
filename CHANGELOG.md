Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。

Keep a Changelog
=================
すべての重要な変更をこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

カテゴリ:
- Added: 新規追加機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ修正

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-26
-------------------
Added
- 初回リリース。KabuSys パッケージの基本機能を実装。
- パッケージメタ:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 外部公開モジュール: data, strategy, execution, monitoring を __all__ に設定。
- 設定・環境変数管理 (src/kabusys/config.py):
  - .env ファイルまたは環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml）。
  - .env/.env.local 読み込み順序を実装（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いを考慮。
  - 必須環境変数チェックを提供（_require）。主要キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - 設定オブジェクト Settings を提供。duckdb/sqlite のデフォルトパス、環境（development/paper_trading/live）とログレベル検証メソッドを含む。
- AI（自然言語処理）モジュール (src/kabusys/ai):
  - ニュースセンチメントスコアリング: score_news を公開（gpt-4o-mini, JSON mode を利用）。
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムしてバッチ送信。
    - バッチサイズ、チャンク処理、JSON レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 置換ロジック（DELETE→INSERT）を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフ。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を内部参照しない設計。
  - 市場レジーム判定: regime_detector モジュールを追加。
    - ETF 1321（日経225連動型）の200日MA乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成し日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュースの抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
- 研究（Research）モジュール (src/kabusys/research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の算出（prices_daily を使用）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新レコード使用）。
    - 設計: DuckDB 接続を受け取り、SQL（ウィンドウ関数等）中心で高速に計算。データ不足時は None を返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効サンプル < 3 の場合は None。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め処理で ties を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
    - 依存を標準ライブラリに限定（pandas 等に依存しない実装）。
- データ（Data）モジュール (src/kabusys/data):
  - カレンダー管理 (calendar_management.py):
    - JPX カレンダー管理、is_trading_day/next_trading_day/prev_trading_day/get_trading_days/is_sq_day といった営業日判定ユーティリティを実装。
    - market_calendar テーブルがない場合は曜日ベースでフォールバック。DB 登録値優先の一貫した補完ロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを実装。
  - ETL パイプライン (pipeline.py) と ETLResult の公開 (etl.py):
    - 差分フェッチ、保存（jquants_client 経由・冪等保存）、品質チェック（quality モジュール）を想定した ETLResult dataclass を提供。
    - _get_max_date やテーブル存在確認ユーティリティを含む。
  - jquants_client / quality 等のクライアント類を想定した連携ポイントを用意（詳細実装は別モジュール想定）。
- データベース:
  - 内部で DuckDB を中心に利用（関数引数に DuckDB 接続を受け取る設計）。
  - sqlite 用の path 設定も提供（monitoring 用等）。
- OpenAI / 外部 API:
  - OpenAI SDK（OpenAI クライアント）を利用して gpt-4o-mini を呼び出す実装。JSON mode（response_format={"type":"json_object"}）を使用。
  - API 呼び出しはリトライや HTTP 5xx の扱いを明確化し、失敗時は例外を上位に伝播しないフェイルセーフ設計（特に AI 評価はスコア 0 やスキップへフォールバック）。
- ロギング:
  - 各モジュールで logging.getLogger(__name__) を利用し詳細ログ（info/debug/warning/exception）を出力する設計。
- ドキュメンテーション:
  - 各モジュールに処理フロー・設計方針・注意点を記載したモジュールドキュメントストリングを充実させている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 注意事項
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を送出する処理が多く存在する点に注意。
- .env パーサーは多くのケースに対処するが、機微な .env 仕様差異は実運用で確認推奨。
- DuckDB の executemany 周り（空リスト不可等）の互換性考慮があるため、DB 操作時のパラメータチェックが入っている。
- 本リポジトリでは「ルックアヘッドバイアス」を避ける設計（date.today() の直接参照禁止、DB クエリに date < target_date 等）を徹底している。

今後の想定改善点（例）
- ai モジュールの unit テスト向けモック抽象化の公開拡張
- jquants_client / kabu 関連の統合テストとエラーハンドリング強化
- モデル切替やプロンプト管理の外部化（設定ベース）

（以上）