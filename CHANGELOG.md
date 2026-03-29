CHANGELOG
=========
（このファイルは Keep a Changelog の形式に準拠しています。）
https://keep-a-changelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージ構成:
    - kabusys.config: 環境変数・設定管理（.env / .env.local の自動読み込み、プロジェクトルート検出）。
    - kabusys.ai: ニュースNLP と市場レジーム判定を実装する AI 関連モジュール
      - news_nlp.score_news: ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む。
      - regime_detector.score_regime: ETF 1321 の 200日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime に日次判定を保存。
    - kabusys.data: データ取得・ETL・カレンダー管理
      - pipeline.ETLResult: ETL の結果表現（再エクスポート via data.etl）。
      - calendar_management: JPX カレンダーの管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job）。
      - pipeline: 差分取得・保存・品質チェックを行う ETL ユーティリティ（バックフィル・健全性チェックを含む）。
    - kabusys.research: ファクター計算・特徴量探索
      - factor_research: calc_momentum（モメンタム、MA200 乖離）、calc_volatility（ATR・出来高等）、calc_value（PER・ROE）など。
      - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearman IC）、rank（同順位平均ランク）、factor_summary（統計サマリ）。
    - パッケージ公開 API の初期エントリポイントを整備（src/kabusys/__init__.py）。
- 環境変数ローダ:
  - プロジェクトルートを __file__ から探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - export KEY=val フォーマット、シングル／ダブルクォート内のバックスラッシュエスケープ、行内コメント処理などを考慮した堅牢なパーサ実装。
  - .env.local は .env を上書き（OS 環境変数は保護される）。
- Settings クラス:
  - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - デフォルト値（KABUSYS_ENV=development、KABUS_API_BASE_URL のデフォルト等）と妥当性チェック（env, log_level の検証）。
  - DuckDB / SQLite のデフォルトパス設定。
- AI モジュールの設計/実装上の重要点:
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーションを明確化。
  - バッチ処理（news_nlp: 最大20銘柄/チャンク）・トークン肥大対策（記事数・文字数上限）を実装。
  - リトライ（指数バックオフ）・失敗時のフォールバック（API失敗時はマクロセンチメント=0.0、スコア取得失敗時は該当チャンクをスキップ）を実装しフェイルセーフに設計。
  - テスト容易性のため、OpenAI 呼び出しラッパー（_call_openai_api）はモック差し替え可能に実装。
- DB 書き込みの冪等化:
  - score_regime / score_news / calendar_update_job / ETL などの書き込みは、部分失敗を避けるために削除→挿入やトランザクション（BEGIN/DELETE/INSERT/COMMIT）で実装。失敗時は ROLLBACK を試行。
  - ai_scores の更新は取得できたコードのみ置換することで部分失敗時に既存データを保護。
- カレンダー管理:
  - market_calendar が未取得の場合は曜日ベースのフォールバック（週末は非営業日）。
  - calendar_update_job はバックフィル（直近 _BACKFILL_DAYS 日）と健全性チェック（将来日数上限）を実装。J-Quants クライアントとの差分取得/保存フローを提供。
- Research モジュール:
  - DuckDB SQL を活用した高速な集約実装（各種 lag/lead / window 関数を活用）。
  - calc_forward_returns は任意ホライズンを受け付け、入力検証（horizons の範囲チェック）あり。
  - calc_ic はスピアマンのランク相関を ties を平均ランクで扱う方式で実装。
- ロギングと診断情報を多所に追加（各処理で情報/警告/例外ログを出力）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Notes / Limitations
- 本ライブラリは DuckDB を前提としたローカル分析環境向け実装。prices_daily / raw_news / raw_financials / market_calendar / ai_scores 等のスキーマが前提。
- OpenAI API を使用するため API キー（OPENAI_API_KEY）または各関数引数に API キーが必要。API 障害時はフェイルセーフ動作するが、スコア欠落が発生する可能性あり。
- .env パーサは多くのケースをカバーするが、極端な特殊ケースは未対応の可能性あり。
- 一部の外部クライアント（jquants_client など）はインターフェースを想定して利用しており、実運用では該当クライアント実装が必要。
- リリース時点で strategy / execution / monitoring の実装はパッケージ公開名に含まれるが、この変更履歴で示したモジュール群が中心（必要に応じて今後追加予定）。

今後の予定（例）
- strategy / execution / monitoring の実装、バックテスト・実稼働連携の追加。
- テストカバレッジ拡充、CI による品質チェックの自動化。
- より細かいメトリクス収集・監視・アラート機能の追加。

--- 
（注）本 CHANGELOG はソースコードからの推測に基づき作成しています。実際のコミット履歴・リリースノートが存在する場合はそちらを優先してください。