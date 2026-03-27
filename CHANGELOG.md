Keep a Changelog
=================

このファイルは Keep a Changelog の形式に従います。
安定バージョン番号は semver を想定します。

[Unreleased]
------------

（現在のスナップショットに基づくリリース履歴はまだありません。）

[0.1.0] - 2026-03-27
-------------------

Added
- 初回公開リリース。以下の主要機能を実装・公開。
  - パッケージのエントリポイント
    - kabusys.__version__ = 0.1.0、top-level __all__ に data/strategy/execution/monitoring を公開。
  - 環境設定管理（kabusys.config）
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応。
    - .env 読み込みは既存OS環境変数を保護するため protected セットを導入し、override ロジックを提供。
    - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等のプロパティを提供）。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の妥当性検証を実装。
  - AI（自然言語処理）モジュール（kabusys.ai）
    - news_nlp.score_news
      - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ問い合わせしてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ冪等的に保存。
      - 時間ウィンドウは前日15:00 JST〜当日08:30 JST を UTC 換算して扱う。バッチサイズや最大文字数等のトークン肥大対策を実装（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
      - JSON Mode 応答のバリデーション、部分失敗時の保護（書き込み対象コードのみ置換）、API リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
      - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch でモック可能）。
    - regime_detector.score_regime
      - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し、market_regime テーブルへ冪等書き込み。
      - マクロニュース抽出はキーワードベース、LLM 呼び出しは gpt-4o-mini を使用（JSON Mode）。API 障害時は macro_sentiment=0.0 のフォールバックで継続。
      - ルックアヘッドバイアス回避のため date 引数ベースで動作し、datetime.today() 等を参照しない設計。
      - 冪等書き込みは BEGIN/DELETE/INSERT/COMMIT で行い、例外時はロールバックを試みる。
  - Data モジュール（kabusys.data）
    - calendar_management
      - market_calendar テーブルを基に営業日判定/前後営業日の取得/get_trading_days/is_sq_day を提供。market_calendar 未取得時は曜日ベースのフォールバック（週末を非営業日として扱う）。
      - JPX カレンダーを J-Quants API から差分取得して market_calendar を更新する calendar_update_job を実装。バックフィル・健全性チェック・最大探索日数等の保護ロジックを含む。
    - ETL パイプライン（pipeline）
      - 差分更新、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュール）を想定した ETLResult データクラスを実装。ETL の収集結果・品質問題・エラー概要を格納可能。
      - ETL 実行時のデフォルトのバックフィルやカレンダー先読み日数を定義。
    - etl モジュールは ETLResult を再エクスポート。
  - Research モジュール（kabusys.research）
    - factor_research
      - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR / ATR% / 平均売買代金 / 出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
      - データ不足時には None を返す等の堅牢な挙動。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
    - research パッケージで主要関数を __all__ としてエクスポート。
  - logging とエラーハンドリング
    - 各モジュールで詳細ログ出力（info/warning/debug）を追加し、API エラー時はリトライやフォールバックで処理を継続する設計（例外は必要時に上位へ伝播）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の重要な設計決定
- ルックアヘッドバイアス回避: AI モジュールおよび研究モジュールは内部で datetime.today() を参照せず、すべて target_date 引数に基づいて計算を行う。
- OpenAI 呼び出しの分離: news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計。テスト時は個別に差し替え可能。
- DB 書き込みは冪等性を重視（DELETE→INSERT など）し、部分失敗時にも既存データを不必要に削除しないよう配慮。
- DuckDB の executemany の制約（空リスト不可等）へ対応するため、空チェックを実装。
- .env パーサは実運用でよくある形式（export、クォート、エスケープ、インラインコメント）に対応。

既知の制限・今後の課題
- 現バージョンでは PBR や配当利回りなどのバリューファクターは未実装（calc_value の注記参照）。
- OpenAI のレスポンス形式に過度に依存しているため、API 仕様変更時はプロンプトやレスポンスパース処理の見直しが必要。
- news_nlp / regime_detector は gpt-4o-mini に依存しているためコスト・レイテンシ考慮が必要。バッチ戦略やローカルモデル対応は今後検討。