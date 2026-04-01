Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-01
--------------------

Added
- 初回リリース: kabusys パッケージ（バージョン 0.1.0）。
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式、引用符付き値（バックスラッシュエスケープを考慮）、インラインコメントの扱い等に対応した堅牢な .env パーサを実装。
  - OS 環境変数の保護（override 引数と protected セット）をサポート。
  - アプリ設定を提供する Settings クラス:
    - J-Quants, kabuステーション, Slack, DB パス（DuckDB/SQLite）、監視閾値、環境（development/paper_trading/live）、ログレベルなどのプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出する _require() を実装。
- AI モジュール（src/kabusys/ai/*）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを纏め、OpenAI (gpt-4o-mini, JSON mode) にバッチ送信して ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト 20 銘柄/回）、1銘柄あたりの最大記事数・最大文字数トリムなどのトークン膨張対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ + リトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score検証、スコアのクリップ）。
    - 部分成功時の安全な DB 書き換え（該当コードのみ DELETE → INSERT）により既存スコアを保護。
    - テスト用フック: _call_openai_api を patch してモック可能。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を算出し market_regime テーブルに冪等保存。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける（news_nlp の内部関数を共有しない）。
    - API 失敗時はマクロセンチメント＝0.0 のフェイルセーフ運用。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時に ROLLBACK）。
    - リトライ、5xx 判定、JSON パース耐性を実装。
- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー取得バッチ（calendar_update_job）と営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベースのフォールバック（週末除外）で一貫した挙動。
    - 最大探索日数制限、バックフィル日数、健全性チェックなど安全機構を実装。
    - jquants_client 経由での差分取得・保存呼び出しを想定。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を導入して ETL 実行結果・品質問題・エラーメッセージを構造化。
    - 差分取得・バックフィル・品質チェック・冪等保存の設計方針を反映（J-Quants API 想定）。
    - data.etl モジュールは ETLResult を再エクスポート。
- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金・出来高比率）等の定量ファクターを DuckDB の SQL と組み合わせて計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 戻し、ルックアヘッドバイアス対策、prices_daily/raw_financials のみ参照する安全設計。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）で LEAD を利用してリターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン ρ をランクにより計算、データ不足時は None。
    - ランク関数（rank）: 同順位は平均ランク、丸めによる ties 対策あり。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を標準ライブラリで計算。
- 共通設計上の堅牢化・運用機能
  - DuckDB を前提とした SQL ベースの処理を中心に実装。
  - ルックアヘッドバイアス防止（target_date を外部から渡す設計）が徹底されている。
  - API 呼び出しの失敗に対して例外をむやみに上げずフェイルセーフで継続する方針（ログ出力・部分スキップ）。
  - テスト容易性のため一部内部 API 呼び出し（_call_openai_api 等）を差し替え可能に設計。
  - ログ出力（logger）を各モジュールで利用。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 環境変数の取り扱いに関する注意:
  - 必須トークン（JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、KABU_API_PASSWORD 等）は Settings のプロパティで必須チェックを行い、未設定時は ValueError を発生させる。
  - .env 自動ロード時に既存の OS 環境変数を保護する実装あり。

Notes
- 内部で参照する外部モジュール（例: jquants_client）はインターフェースを想定して呼び出しているため、実行環境ではそれらクライアントの実装（API キーやネットワーク設定）が必要です。
- OpenAI API を呼ぶ箇所は実際の API キー（環境変数 OPENAI_API_KEY または関数引数）を必要とします。
- 今後のリリースで strategy / execution / monitoring の実装や、より詳細な品質チェックルールの追加を予定しています。

上記はソースコードから推測して作成した初回リリースの変更履歴です。実際のリリースノート作成時は用途に合わせて日付・項目を調整してください。