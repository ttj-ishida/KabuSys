CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
-----------

- なし

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点と設計方針は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージを提供。__version__ = 0.1.0。public API として data, strategy, execution, monitoring を公開。
- 環境変数・設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサの実装（export プレフィックス、クォート／エスケープ、インラインコメントの取り扱い）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ。
  - Settings クラスにより、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定をプロパティで提供（バリデーション含む）。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算 calc_news_window(target_date)（JST ベース→UTC naive datetime）。
  - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）。
  - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。レスポンス検証・スコアのクリップ。
  - テスト用フック: _call_openai_api をパッチで差し替え可能。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime(conn, target_date, api_key=None): ETF(1321) の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ冪等書き込み。
  - ma200 比率のルックアヘッド回避、マクロ記事がない場合や API 失敗時のフェイルセーフ（macro_sentiment=0.0）。
  - OpenAI 呼び出しのリトライ・エラー分類とログ出力。
- データ処理・カレンダー (kabusys.data)
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間バッチ更新 calendar_update_job。
  - jquants_client との連携（fetch/save を呼び出す想定）。DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
  - 安全策: 最大探索日数制限、バックフィル、健全性チェック。
- ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
  - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー）の集約と to_dict によるシリアライズを提供。
  - 差分更新、バックフィル、品質チェックの設計を反映したインタフェース（jquants_client と quality モジュールを利用する想定）。
- 研究用ユーティリティ (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials を用いたファクター計算（モメンタム、バリュー、ATR、流動性等）。
  - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（統計サマリ）、rank（同順位は平均ランクを付与）。
  - 統計処理は外部依存なし（標準ライブラリ + DuckDB SQL）。
- 設計上の挙動・安全性に関する実装
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を多くの主要処理で直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは冪等化（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK パターン）を採用。
  - DuckDB の executemany に対する空リスト問題への注意点（空の場合は呼ばない実装）。
  - OpenAI レスポンスの堅牢なパース（JSON モードの前後ノイズ対応）。

Changed
- 初回リリースにつき変更履歴なし。

Fixed
- 初回リリースにつき修正履歴なし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI / 外部 API キーは api_key 引数か環境変数 OPENAI_API_KEY により注入。キー未設定時は ValueError を送出して明示的に扱う。

Notes（設計上の既知点・注意事項）
- OpenAI とのやり取りは gpt-4o-mini と JSON Mode を使用する想定。API スキーマや SDK の変更により挙動が変わる可能性あり。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない（結合度低減、テスト容易化）。
- API 失敗時のフェイルセーフとして、スコア計算をゼロフォールバックやスキップにする実装が多く含まれる（実運用での監視・アラートを推奨）。
- strategy / execution / monitoring モジュールは public export に含まれるが、今回のコードスニペットには具体的実装を含まない。別途実装予定。

Acknowledgements
- DuckDB を主要なローカル分析 DB として利用する設計。
- J-Quants / kabuステーション 等の外部データソースと連携する前提の実装。

（将来的にリリースごとに追加の変更点・改修点をここに追記してください。）