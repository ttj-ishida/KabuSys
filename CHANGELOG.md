CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
Semantic Versioning を想定しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Deprecated: 非推奨
- Removed: 削除された機能
- Fixed: バグ修正
- Security: セキュリティ関連

Unreleased
----------
- （このセクションは次回リリースで埋めてください）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__="0.1.0" を定義し、data/strategy/execution/monitoring を公開対象として宣言。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーを実装（export プレフィックス、クォート対応、インラインコメント処理、保護されたキーの上書き制御）。
    - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定）。
    - 環境変数の必須チェックで未設定時は ValueError を送出。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。
- AI（ニュースNLP・市場レジーム）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini, JSON Mode）に対してバッチでセンチメント解析を行い ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
    - API 呼び出しでのリトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップを実装。
    - DuckDB 互換性に配慮した DB 書き込み（部分置換: DELETE → INSERT、executemany の空パラメータ回避）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出（キーワードリスト）・OpenAI 呼び出し（JSON Mode）・リトライ/フェイルセーフ処理を実装。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ参照、datetime.today() を参照しない設計）。
- データ処理・ETL
  - src/kabusys/data/pipeline.py
    - ETL の公開用データクラス ETLResult を実装。取得数／保存数／品質問題／エラー情報を保持し、辞書化メソッドを提供。
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client, quality モジュールと連携する想定）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開するエイリアスを追加。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを提供（market_calendar テーブルを前提）。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。DB 登録値優先・未登録は曜日ベースでフォールバック。
    - 夜間バッチ job: calendar_update_job（J-Quants API からの差分取得・バックフィル・健全性チェックを含む）を実装。
    - DuckDB から返る日付値の変換ユーティリティ、テーブル存在チェック等を実装。
- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）等のファクターを DuckDB で計算する関数を実装: calc_momentum, calc_volatility, calc_value。
    - それぞれデータ不足時の挙動（None 戻し）やログ出力を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン相関）計算（calc_ic）、ランキング（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみでの実装を志向。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- ロギング・堅牢性
  - 各モジュールで詳細なログ出力（info/debug/warning）を追加。
  - API 呼び出し失敗時はフェイルセーフ（例: macro_sentiment=0.0 や該当チャンクスキップ）で継続する設計。
  - DuckDB の互換性問題（executemany に空リストを与えない）を考慮した実装。

Changed
- 初版リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- .env ロードで既に存在する OS 環境変数を保護する機構を実装（protected set）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。

Notes / Known issues
- pipeline._get_max_date の末尾がソース切れのように見える断片（return date.fro）が存在します。これは明らかなタイプミス／未完了箇所の可能性があるため、リリース後に修正が必要です。
- パッケージの __all__ に strategy, execution, monitoring が含まれている一方で、それらのモジュール実装は本リリースに含まれていないか、別ファイルにまだ存在しない可能性があります（将来実装予定）。
- OpenAI API を利用する機能（news_nlp, regime_detector）は実行時に OPENAI_API_KEY が必要。未設定時は ValueError を送出するため、運用時にキーの設定が必要。
- 現在の設計では ai スコア等が ±1.0 にクリップされること、部分失敗時に DB の既存データを保護するために書き換え範囲を限定することを意図的に行っています。運用上の要件に応じて調整してください。
- unit テスト向けに _call_openai_api 等の内部関数が差し替え可能に設計されています。テスト実装時にモックを利用してください。

作者／メンテナ
- KabuSys プロジェクトチーム

（注）本 CHANGELOG は与えられたソースコードを基に推測して作成しています。実際のコミット履歴や意図と差異がある場合があります。