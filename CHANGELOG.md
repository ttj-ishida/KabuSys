# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従い、セマンティックバージョニングを採用しています。

- フォーマット: Keep a Changelog
- 参照: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- パッケージメタ情報
  - src/kabusys/__init__.py に初期バージョン __version__ = "0.1.0" を追加。

- 環境設定 / ロード
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を上位探索して決定）。
    - .env, .env.local の優先順位を尊重し OS 環境変数を保護（.env.local は override）。
    - export KEY=val 形式、クォートやエスケープ、インラインコメントの取り扱いに対応するパーサ実装。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack, DB パス, 環境 / ログレベル検証など）。
    - 設定値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。未設定の必須環境変数は ValueError で明示。

- AI ベースのニュース / レジーム判定機能
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを銘柄毎に集約し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメントスコアを計算。
    - JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して扱う calc_news_window を実装。
    - API 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフを実装。
    - レスポンス検証ルールを実装（JSON 抽出、results 配列・code/score チェック、数値の有限性検査、スコア ±1.0 でクリップ）。
    - 大規模処理向けにバッチ（最大 20 銘柄）での送信、1 銘柄あたりの最大記事数・文字数トリムを実装。
    - 部分失敗対策として、書き込み時は対象 code に限定して DELETE → INSERT（冪等性保護）。
    - テスト性向上のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）とした。

  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離と、ニュース由来のマクロセンチメントを組み合わせて日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）、マクロニュース抽出、LLM 呼び出し、重み付け合成（70% MA, 30% マクロ）、閾値判定を実装。
    - OpenAI 呼び出しは専用実装。API エラー時は macro_sentiment を 0.0 としてフォールバック。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行。失敗時は ROLLBACK を試行して例外を伝播。

- データ基盤ユーティリティ
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）用ロジックを実装：営業日判定（is_trading_day）、次/前営業日探索（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）、SQ 判定（is_sq_day）。
    - DB にカレンダーデータがない場合の曜日ベースフォールバックを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアントを介した差分取得・バックフィル・健全性チェックを実行。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の公開インターフェース（ETLResult データクラス）を実装し、差分取得・保存・品質チェックの結果を集約できるように設計。
    - ETLResult は取得数/保存数・品質問題・エラー一覧を持ち、has_errors / has_quality_errors / to_dict を提供。
    - DuckDB を前提としたテーブル存在チェック・最大日付取得ユーティリティを実装。

- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン & ma200 乖離）、ボラティリティ（20日 ATR）・流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）などのファクター計算を実装。
    - DuckDB SQL を用いた窓関数実装、データ不足時の None 処理、ログ出力を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ρ）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - 外部依存を用いず標準ライブラリのみで実装。

- テスト・運用性向上のための配慮
  - 各モジュールで datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。
  - OpenAI 呼び出し箇所はモック差替え可能にしてユニットテストを容易に。
  - DuckDB での executemany 空リスト問題を回避するためのチェックを追加。
  - ロギングと警告を多用しエラー時のフォールバック挙動を明示的に記録。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

注記:
- OpenAI の利用には環境変数 OPENAI_API_KEY（または関数引数）を必須とする箇所があり、未設定時は ValueError を送出します。
- 設定や DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）はコード内の前提に従って作成してください。
- 実運用に際しては Slack トークン、kabu API パスワード、J-Quants トークン等の機密情報の管理に注意してください（Settings で必須チェックあり）。