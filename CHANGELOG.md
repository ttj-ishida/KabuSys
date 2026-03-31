# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

最新リリース
=============

0.1.0 - 2026-03-31
------------------

初回公開リリース。本リポジトリに含まれる主な機能・実装方針は以下の通りです。

Added（追加）
- パッケージ基盤
  - pakage 初期化: kabusys パッケージのバージョンを `__version__ = "0.1.0"` として定義。公開 API として data/strategy/execution/monitoring をエクスポート。
- 環境設定読み込み（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。J-Quants / kabu ステーション / Slack / DB パスや動作環境（development/paper_trading/live）などのプロパティを提供。
  - プロジェクトルート自動検出実装（.git または pyproject.toml を基準）により CWD に依存せず .env を検索。
  - .env パーサーを実装: export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いを考慮した堅牢なパース処理。
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - OS 環境変数を保護するための上書き/保護ロジック（.env.local を .env の上位にして上書き可能だが、既存 OS 環境変数は protected）。
- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ問い合わせし、センチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - JST 時刻ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して対象記事を抽出するユーティリティ（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字トリム）、JSON Mode 応答パース、レスポンスバリデーションを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は部分的スキップして他銘柄を保護する設計。
    - テスト容易化のため OpenAI 呼び出し関数（_call_openai_api）をパッチ差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等的に書き込む処理を実装（score_regime）。
    - マクロニュースはキーワードベースで抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してセンチメントを取得。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用する設計。OpenAI 呼び出しは独立実装でモジュール結合を低く保つ。
- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー（market_calendar）を用いた営業日判定 API を実装: is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day。
    - market_calendar が未取得の場合は曜日ベース（平日＝営業日）でフォールバックする一貫した挙動。
    - 夜間バッチで J-Quants から差分取得して market_calendar を冪等的に更新する calendar_update_job を実装（バックフィル・健全性チェック含む）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化して返す機能を提供。
    - 差分更新／バックフィル／品質チェックの設計方針を反映（品質チェックは収集して継続する方針）。
  - etl モジュールから ETLResult を再エクスポート。
  - jquants_client を利用したデータ取得・保存の想定（実装は外部モジュール）。
- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - ボラティリティ／流動性（calc_volatility）: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）: raw_financials から EPS/ROE を結合し PER/ROE を算出（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL ベースの実装で、外部 API へのアクセスなし・本番口座に影響を与えない設計。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンの将来リターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの順位相関を実装（同順位は平均ランクで扱う）。
    - ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない標準ライブラリのみでの実装。
- API キーとエラー処理
  - OpenAI API キーは関数引数経由または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する明示的な挙動。
  - DuckDB に対する書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。書き込み失敗時は ROLLBACK を試行し、ログを残す。

Changed（設計・方針）
- 全体設計方針として「ルックアヘッドバイアス防止」を明示的に採用
  - datetime.today() / date.today() を直接参照しない。関数は必ず target_date を引数として受け取り、その前日以前のデータのみを参照するよう実装。
- 部分失敗時の保護
  - AI スコアリングや ETL の保存処理では、部分失敗があっても他の既存データを消さないようにコード単位で DELETE → INSERT を行う（部分的に書き換える方針）。
- テスト性向上
  - OpenAI への実際の呼び出しは内部関数を経由することで unittest.mock.patch により差し替えやすくしている。

Fixed（修正）
- （初回リリースにつき過去の修正履歴は無し。実装内に注意ログやフォールバック処理を多く盛り込み、実運用での障害耐性を向上させている旨を反映。）

Security（セキュリティ関連）
- API キーの扱いは関数引数または環境変数のみとし、ログにキーを出力しない方針を採用。
- .env 読み込みにおいて OS 環境変数を保護（.env による上書きを制限）する仕組みを実装。

Notes（備考 / 実装上の注意）
- DuckDB の executemany に空リストが渡せない（0.10 系の挙動）ため、空チェックを行ってから executemany を呼ぶ実装になっている。
- OpenAI 呼び出しは JSON モード応答を期待しているが、エッジケースとして余分な前後テキストが混入する場合に備えた復元処理を含む。
- market_calendar のデータがまばらな場合でも next_trading_day / prev_trading_day / get_trading_days の挙動が一貫するよう設計されている。
- 各モジュールは本番口座や発注 API にアクセスしないことを明示（研究・データ処理用の安全設計）。

今後の予定（例）
- strategy / execution / monitoring の実装拡充（現状はパッケージエクスポートのみ）
- 追加の品質チェックルールや監査ログの強化
- モデル選択やプロンプト改善による LLM スコアの精度向上

----- 

注: 上記は現行ソースコードから推測できる実装内容・設計方針を基に作成した CHANGELOG です。実際のリリースノート作成時はコミット履歴やリリース差分に基づく追記・修正を行ってください。