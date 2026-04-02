CHANGELOG
=========
すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Security）に分類しています。
- 版は Semantic Versioning に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-02
--------------------
初回リリース。以下の主要機能・モジュールを実装・公開しました。

Added
- 基本パッケージ
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。公開 API として data, research, ai, ... を __all__ に定義。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパースは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
  - OS 環境変数を保護する protected 機能と override フラグを実装。
  - Settings クラスを提供（J-Quants/kabu API/Slack/DBパス/監視閾値/環境・ログレベル検証などのプロパティ）。
  - 必須環境変数未設定時に明確なエラーメッセージを返す _require 実装。
- AI（自然言語処理・レジーム判定）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で一括バッチ評価（最大20銘柄／チャンク）。
    - JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30 JST）を calc_news_window で提供。
    - 1銘柄あたりの記事トリム（記事数／文字数制限）によるトークン肥大対策。
    - 再試行（429/ネットワーク/タイムアウト/5xx）、指数バックオフ、レスポンス構文チェック、スコアの ±1.0 クリップ、部分書き換え（DELETE→INSERT）による冪等性と部分失敗保護。
    - score_news(conn, target_date, api_key=None) による ai_scores テーブル書き込み API。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）判定。
    - OpenAI 呼び出しのリトライ、API障害時のフェイルセーフ（macro_sentiment=0.0）、レスポンス JSON パースガードを実装。
    - ルックアヘッドバイアス防止（target_date 未満のみを参照、datetime.today() を参照しない方針）。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照する営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・保存処理（jquants_client 経由）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラス（target_date, fetched/saved カウント, quality_issues, errors）と to_dict（品質問題の辞書化）を実装。
    - 差分取得・バックフィル・品質チェックを念頭に置いた設計。
    - etl モジュールで ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR（平均）、相対ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials の最新財務データと株価から PER / ROE を算出。
    - DuckDB を利用した SQL ベースの実装で外部 API にアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで計算。horizons 引数の検証あり。
    - calc_ic: スピアマンの順位相関（Information Coefficient）を実装（同順位は平均ランクで処理）。
    - rank / factor_summary: ランク算出・統計サマリー（count/mean/std/min/max/median）。
    - pandas 等に依存しない標準ライブラリのみでの実装。
- テスト容易性・拡張性
  - OpenAI 呼び出し箇所を _call_openai_api 関数に切り出し、ユニットテスト時にモック差し替え可能。
  - DuckDB の executemany における空リスト問題への対応（空時は実行しないガード）。
  - ログ出力・警告を各所に追加し障害解析を容易に。

Fixed / Robustness improvements
- OpenAI レスポンスのノイズ（JSON 前後の余計なテキスト）に対する復元ロジックを追加。
- API エラー分類に基づくリトライ制御（5xx はリトライ、非5xx は即時フォールバック）。
- レスポンスパース失敗や API 完全障害時にシステム全体を停止させずフェイルセーフで処理を継続する設計。
- DuckDB 日付値の安全な date オブジェクト変換ユーティリティを追加。
- calendar_update_job にて将来日付の異常値チェック（SANITY_MAX_FUTURE_DAYS）を追加。

Known limitations / Notes
- OpenAI クライアント（OpenAI SDK）と jquants_client / quality モジュールは外部依存。実行環境にこれらの設定（APIキー等）が必要。
- 一部モジュールは外部 API 呼び出し（OpenAI / J-Quants）を行うため、実行にはネットワーク接続と適切な認証情報が必要。
- 本リリースは初期版のため、さらなる最適化（パフォーマンス改善・追加品質チェック等）が今後の課題。

Acknowledgements / Design choices
- ルックアヘッドバイアスを避けるため、全てのスコアリング／判定関数は内部で datetime.today()/date.today() を直接参照しない方針。
- DB 書き込みはできるだけ冪等に（DELETE→INSERT 等）して部分失敗時に既存データを保護。
- 外部ライブラリ依存を最小化し、ユニットテスト容易性を考慮した分離設計を採用。

（以上）