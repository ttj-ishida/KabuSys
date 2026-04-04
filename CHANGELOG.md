Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを採用します。

[0.1.0] - 2026-04-04
--------------------

Added
- 初回公開リリース: KabuSys 日本株自動売買システム 基本モジュール群を追加。
  - パッケージメタ:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パブリックサブパッケージ: data, strategy, execution, monitoring を公開。
  - 設定 / 環境変数管理 (src/kabusys/config.py)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export KEY=value 形式、クォート・エスケープ、行末コメントなどに対応したパーサ実装。
    - 環境値の保護機能（既存 OS 環境変数を上書きしない / .env.local で上書き可能）。
    - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境 / ログレベル等）。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装（許容値チェック）。
  - AI（自然言語処理） (src/kabusys/ai)
    - ニュース NLP（score_news） (src/kabusys/ai/news_nlp.py)
      - raw_news と news_symbols を集約して銘柄ごとにテキストをまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄毎のセンチメントを ai_scores テーブルへ書き込む。
      - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換）を対象。 calc_news_window を提供。
      - バッチ処理（最大20銘柄）、1銘柄あたり記事トリム（最大記事数/文字数）でトークン肥大化を抑制。
      - JSON レスポンスの堅牢なバリデーション・パース（余分なテキストを含む場合の復元処理など）。
      - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ、失敗時は該当チャンクをスキップして継続。API 呼び出し箇所はテストで差し替え可能（_call_openai_api を patch 可能）。
      - データベース書き込みは部分置換（対象コードに限定した DELETE → INSERT）で冪等性・部分失敗耐性を確保。
    - 市場レジーム判定（score_regime） (src/kabusys/ai/regime_detector.py)
      - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）を判定・保存。
      - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）でセンチメントを取得。
      - API エラー時は macro_sentiment=0.0 のフェイルセーフ、計算結果は -1.0〜1.0 にクリップ。
      - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行。
  - Research（解析/リサーチ） (src/kabusys/research)
    - factor_research モジュール (src/kabusys/research/factor_research.py)
      - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。
      - ボラティリティ・流動性: 20日 ATR（atr_20）・相対 ATR（atr_pct）・20日平均売買代金・出来高比率を計算。
      - バリュー: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0/欠損時は None）。
      - DuckDB を用いた SQL+ウィンドウ関数実装、データ不足時は None を返す仕様。
    - feature_exploration モジュール (src/kabusys/research/feature_exploration.py)
      - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを LEAD を使って一括取得。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（ties は平均ランク処理）。
      - 基本統計量集計（factor_summary）とランク関数（rank）を提供。
    - 研究系ユーティリティを再エクスポート（__all__）。
  - Data（データ基盤関連） (src/kabusys/data)
    - カレンダー管理（calendar_management.py）
      - market_calendar をベースに営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を実装。
      - DB データ優先、未登録日は曜日ベースのフォールバック。最大探索日数上限を設定して無限ループを回避。
      - calendar_update_job: J-Quants クライアントを使った差分取得・バックフィル・健全性チェック（未来日付の異常検出）・冪等保存を実装。
    - ETL パイプライン（pipeline.py / etl.py）
      - ETLResult データクラスを公開（etl.ETLResult を再エクスポート）。
      - 差分取得、保存（jquants_client の save_* を呼ぶ想定）、品質チェック（quality モジュール）を行う設計を反映したユーティリティ群。
      - バックフィル、カレンダー先読み、品質問題は収集して返す（Fail-Fast ではなく呼び出し元に委ねる設計）。
  - 依存・外部サービスとの接続
    - DuckDB を想定した DB 操作。
    - OpenAI（gpt-4o-mini）を JSON mode で利用する実装。
    - J-Quants / kabuステーション / LINE API 用の設定キーを Settings で提供（環境変数に依存）。

Changed
- 初回リリースのため「Changed」はありません。

Fixed
- 初回リリースのため「Fixed」はありません。

Notes / 重要な運用情報
- 必須環境変数:
  - OPENAI_API_KEY（AI モジュールを利用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - .env.example を参考に .env を作成してください。
- 自動 .env 読み込みはパッケージがインストール後も動作するよう .__file__ を基準にプロジェクトルートを探索します。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI モジュールは外部 API の失敗に対してフェイルセーフ（0 やスキップ）で継続する設計です。部分失敗時も DB の既存データを過剰に削除しないよう配慮しています。
- OpenAI 呼び出し箇所はユニットテストで差し替え可能（_call_openai_api を patch）になっています。
- 全体的に「ルックアヘッドバイアスを避ける」設計方針を採用しています（datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す等）。

Acknowledgements / 既知の制約
- DuckDB の executemany の空引数に関する制約を回避する実装が含まれます（空リストを渡さないガード）。
- OpenAI SDK のエラー型差異（status_code の有無など）に備えた堅牢化処理を実装しています。

今後の予定（概略）
- strategy / execution / monitoring の具象実装（注文発行・監視ループ・運用 UI など）の追加。
- 品質チェック（quality モジュール）の詳細実装と ETL の監査ログ強化。
- テストカバレッジ拡充と CI の整備。

Unreleased
----------
- 現時点では未リリースの変更はありません。