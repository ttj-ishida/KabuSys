KEEP A CHANGELOG
=================

このCHANGELOGは「Keep a Changelog」形式に準拠しています。
全ての重要な変更点を記録します。

[Unreleased]
------------

- なし（初回リリースは 0.1.0 を参照してください）

0.1.0 - 2026-03-27
------------------

初回公開リリース。以下の主要機能と設計方針を実装しています。

Added
- パッケージ基盤
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。公開 API として data/strategy/execution/monitoring を __all__ でエクスポート。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応したパーサ実装。
  - OS 環境変数の保護（既存キーを protected として上書き抑止）、override 動作を提供。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ設定（J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等）をプロパティ経由で取得。必須項目未設定時は明確な ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セットを定義）。
- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約・トリムして OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を算出。
    - バッチサイズ、1銘柄あたりの記事数制限、文字数トリム制限を導入してトークン肥大を抑制。
    - JSON Mode を使った厳格なレスポンス処理と堅牢なバリデーション実装（部分的に前後テキストが混ざっても {} を抽出して復元）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ、失敗時は当該チャンクをスキップするフェイルセーフ。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - datetime.today()/date.today() を使わず、外部から渡した target_date に基づくタイムウィンドウ設計（ルックアヘッドバイアス防止）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタリング、最大件数制限、OpenAI 呼び出しに対するリトライとフォールバック（API 失敗時は macro_sentiment = 0.0）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - こちらもルックアヘッドバイアス防止の設計を採用。
  - OpenAI 呼び出しはモジュール内で独立実装（テスト用に patch 可能）し、news_nlp と regime_detector は意図的に内部 helper を共有しない設計でモジュール結合を低減。
- リサーチ機能（kabusys.research）
  - factor_research: Momentum / Volatility / Value 等の定量ファクター計算を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: 最新の raw_financials と当日の株価から PER, ROE を計算。
    - DuckDB のウィンドウ関数を活用した実装、date と code をキーとした整形された出力リストを返す。
    - ルックバック用のスキャン範囲バッファやデータ不足ハンドリングを含む。
  - feature_exploration: 将来リターン算出、IC（スピアマンランク相関）計算、rank ユーティリティ、factor_summary（統計サマリー）を提供。
    - calc_forward_returns は複数ホライズンを同時取得する効率的クエリを実装。horizons のバリデーションを行う。
    - calc_ic は None や非有限値を除外し、有効サンプル数が少ない場合に None を返す安全設計。
    - rank は同順位の平均ランク処理を行い、浮動小数の丸めで ties 判定を安定化。
- データプラットフォーム（kabusys.data）
  - calendar_management: market_calendar を扱うマーケットカレンダー管理ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータが無い場合は曜日ベースのフォールバック（土日を非営業日）で一貫して動作。
    - 最大探索日数制限や健全性チェック（過度に未来の日付のスキップ）、バックフィルロジックを実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新するバッチ処理を実装。fetch/save の失敗は安全に処理される。
  - pipeline / etl: ETL パイプライン関連
    - ETLResult データクラスを公開し、ETL の収集メタ情報（取得数、保存数、品質問題、エラー）を構造化して返却可能。
    - 差分取得、バックフィル、品質チェック（品質問題は収集して呼び出し元で判断）という設計方針を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - jquants_client / quality との連携を想定した設計（save_* / fetch_* を呼ぶ責務分離）。
- データベース
  - DuckDB を主要なストレージ/クエリ層として採用。各モジュールは DuckDB 接続を受け取って SQL を実行する設計。
- ロギングとフェイルセーフ
  - API エラー/パースエラー時の警告ログ出力を徹底。LLM/API の失敗は基本的にスキップや中立化（0.0 / None）で継続する設計。
  - DB 書き込みはトランザクションを用いた冪等処理（DELETE → INSERT）で安全に実施。失敗時は ROLLBACK を試行し、失敗ログを残す。

Changed
- 初期リリースのため該当なし（このリリースで主要機能を導入）。

Fixed
- 初期リリースのため該当なし（実装上のフェイルセーフやログ出力を含む安定化を意図して実装済み）。

Security
- 環境変数（OpenAI API キー、Slack トークン、Kabu API パスワード、J-Quants トークンなど）を Settings 経由で必須チェック。未設定時は明示的なエラーを出す。
- OS 環境変数を意図せざる上書きから保護する仕組みを導入。

Notes / Implementation Remarks
- ルックアヘッドバイアス防止: AI スコアリングやレジーム判定、ETL の日付ロジックでは datetime.today()/date.today() を直接参照せず、外部から渡された target_date に基づいて処理を行う設計を採用。
- OpenAI 呼び出しはテスト容易性のため patch 可能な内部関数を用意。
- DuckDB の executemany の制約（空リスト不可）を考慮した実装（空チェックの上で executemany 実行）。
- JSON Mode を利用することで LLM 出力の安定性を高めているが、稀に混入する余計なテキストを復元するロジックも実装。

今後の予定（例）
- Strategy / execution / monitoring の実装強化と統合テスト
- J-Quants / kabu クライアント実装の追加・改善
- テストカバレッジの拡充と CI ワークフロー整備
- モデル切替オプションやスコア算出のハイパーパラメータ公開

-----

変更履歴に不明点がある場合や追加で反映したい差分があれば教えてください。