Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注意: 下記はコードベースから推測して作成した変更履歴です。実際のコミット履歴がある場合はそちらを優先してください。

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初期リリース。
- パッケージメタ:
  - バージョンを kabusys.__version__ = "0.1.0" として公開。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を設定。
- 設定／環境変数管理 (kabusys.config):
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動探索（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しない読み込みを実現。
  - .env パーサーはコメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 自動ロードの無効化用に環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - 環境変数未設定時は ValueError を投げる _require() と、各種設定プロパティを持つ Settings クラスを公開。
  - サポートされる環境値チェック（KABUSYS_ENV, LOG_LEVEL）とデフォルト値（KABUS_API_BASE_URL, DBパスなど）。
- AI モジュール (kabusys.ai):
  - ニュース NLP スコアリング (news_nlp.score_news):
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - バッチサイズ、文字数・記事数の上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション、スコアのクリップを実装。
    - 成果は ai_scores テーブルへ冪等に（DELETE → INSERT）保存。部分失敗時に既存データを保護する設計。
    - target_date ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算する calc_news_window を公開。
    - テスト用に内部の OpenAI 呼び出し関数をパッチ可能に設計。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321（日経225連動）に対する 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）のリトライとフォールバック（失敗時 macro_sentiment=0.0）、レジームスコアのクリップと閾値（bull/bear）判定、market_regime への冪等書き込みを実装。
    - LLM 呼び出しは別実装とし、モジュール結合を避ける設計（テスト容易性を考慮）。
- Research モジュール (kabusys.research):
  - factor_research:
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR(20) 等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB に対する SQL ベースの実装。データ不足時の None ハンドリング、ログ出力あり。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンまでのリターンを一括取得する最適化クエリ。
    - IC（スピアマン順位相関）計算（calc_ic）およびランク変換（rank）。
    - ファクター統計サマリー（factor_summary）。
  - 研究用ユーティリティの再エクスポート（zscore_normalize 等）。
- Data モジュール (kabusys.data):
  - カレンダー管理 (calendar_management):
    - market_calendar を利用した営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数制限など堅牢な設計。
    - JPX カレンダーを J-Quants API から差分取得して market_calendar を更新する夜間バッチ仕事（calendar_update_job）を実装。バックフィル、サニティチェック、例外処理あり。
  - ETL パイプライン (pipeline, etl):
    - 差分取得 → 保存（jquants_client の save_* を利用）→ 品質チェック（quality モジュール）という ETL ワークフローを想定したユーティリティ。
    - ETLResult データクラスを公開し、取得数・保存数・品質問題・エラーを集約して返す仕組みを提供。
    - テスト容易性のため id_token/api_key を注入可能とする設計（呼び出し元で注入可能）。
  - jquants_client との連携ポイントを用意（fetch/save を想定）。
- 実装品質・設計上の注意点:
  - ルックアヘッドバイアス防止のため、いずれの処理も datetime.today() / date.today() を直接参照しない設計（target_date を引数に取る）。
  - OpenAI 呼び出し失敗時はフェイルセーフ動作（スコア 0.0 やスキップ）を行い、処理全体の継続を優先。
  - DuckDB のバージョン差異（executemany の空リスト等）に配慮した実装上の注意あり。
  - テスト容易性のため内部 API 呼び出しを patch 可能にしている箇所がある。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決され、未設定時は明示的なエラーを発生させる仕組みを実装。
- .env 読み込み時に OS 環境変数を保護する機能（読み込み順序と protected set）を実装。

既知の注意点 / 制約
- OpenAI 呼び出しは gpt-4o-mini の JSON モードを想定しており、APIのレスポンス形式が変わるとパースエラーとなる可能性がある（パース失敗時はフェイルセーフでスコア 0.0 やスキップ）。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api 実装を持つ（モジュール間でプライベート関数を共有しない設計）。テスト時はそれぞれをモックする必要がある。
- calendar_update_job や ETL 処理は jquants_client の実装に依存するため、本番接続時は該当クライアントの挙動に注意。

貢献
- このリリースはコードベースから推定して作成しました。実際の貢献者・コミットログはプロジェクトの VCS を参照してください。

(補足) 推奨する次の改善案
- CI テストを整備して OpenAI 呼び出しをモックするテストケースを追加する。
- jquants_client の実装例・テストフィクスチャを提供して ETL のローカル検証を容易にする。
- strategy / execution / monitoring モジュールの実装・ドキュメントを追加し、エンドツーエンド動作をカバーする統合テストを構築する。