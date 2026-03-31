# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは主にコードベースから推測できる機能追加・設計方針・既知の挙動を記載しています。

フォーマット:
- 重大な変更は Breaking changes に分類します（現時点では該当なし）。
- 日付はリリース日を示します。

ver. 0.1.0 - 2026-03-31
---------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージ公開用のエントリポイント: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
- 環境変数・設定管理モジュール（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - 行解析で export 形式、クォート（シンプルなエスケープ処理含む）、インラインコメント処理をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境種別・ログレベル等をプロパティ経由で取得。値検証（有効な環境名・ログレベルの検査）と必須変数チェックを行う。
- AI 関連モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）に JSON Mode で問い合わせて銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ送信（最大 20 銘柄/チャンク）、記事数・文字数上限、レスポンスのバリデーション、スコアのクリップ ±1.0 を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。API 呼び出し失敗時はフェイルセーフによりスキップして継続。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT）を実装。DuckDB の executemany の空リスト問題へ配慮。
    - calc_news_window 実装：JST 基準のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換して返すユーティリティを提供。
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書込み銘柄数）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily から MA 乖離を算出（ルックアヘッド回避のため target_date 未満のデータのみ使用）。データ不足時は中立 (1.0) を採用して安全化。
    - raw_news からマクロキーワードで抽出したタイトルを LLM に送りマクロセンチメントを算出（記事が無ければ LLM コールしない）。
    - OpenAI 呼び出しは独立実装。API リトライ（バックオフ）・エラー時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへの冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1=成功、API キー未指定なら ValueError）。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定／前後営業日探索／期間の営業日取得／SQ日判定を実装。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動を保証。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・正当性チェックを含む）。
    - _has_calendar_data や _to_date 等のユーティリティを実装して堅牢化。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開し、取得数・保存数・品質問題・エラーを集約して返す設計。
    - 差分更新・バックフィル・品質チェック（kabusys.data.quality を想定）を考慮した設計。
    - jquants_client との連携（fetch/save 機能を利用）を想定した実装骨子。
    - 内部ユーティリティとしてテーブル存在確認や最大日付取得（_get_max_date）等を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、20 日平均売買代金、出来高変化率、PER/ROE（raw_financials ベース）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。
    - データ不足時は None を返す設計で堅牢化。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - 外部依存を持たない純粋 Python 実装で、ties の扱い・丸めによる比較誤差対策などが含まれる。
- テスト／運用面の配慮
  - OpenAI 呼び出しや自動 .env ロードをテスト環境向けに差し替え可能（関数を patch 可能／KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - ルックアヘッドバイアス回避のため、各モジュールで date.today()/datetime.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DuckDB 特有の挙動（executemany の空リスト不可）への対応。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Known limitations / Notes
- 実行には OpenAI API キー（環境変数 OPENAI_API_KEY または各関数引数）および J-Quants API クライアント（kabusys.data.jquants_client）が必要。
- DuckDB のバージョン依存（executemany の挙動等）に注意。コード中に互換性配慮のコメントを多数含む。
- ニュース収集ウィンドウや時間扱いは UTC naive datetime を採用しており、データベース内の raw_news.datetime が UTC で保存されている前提。
- OpenAI レスポンスは JSON 形式を厳密に期待しているため、LLM の出力フォーマットが崩れるとバリデーションでスキップされる（フェイルセーフとして継続）。
- 一部設計・実装方針（例: スコア合成比率や閾値、モデル名 gpt-4o-mini の選定など）はハードコーディングされており、将来的に設定化する余地がある。

参考（実装上の主な挙動）
- .env の読み込み順: OS 環境 > .env > .env.local（ただし .env.local は override=True で後から上書き）。
- settings.env は 'development' / 'paper_trading' / 'live' のみ有効で、それ以外は ValueError。
- score_news は成功時に書き込んだ銘柄数を返す。score_regime は成功時に 1 を返す。
- 各 AI 呼び出し関数は特定の例外（429/接続エラー/タイムアウト/5xx）をリトライ対象とし、それ以外はスキップしてログを残す設計。

今後の改善候補（提案）
- OpenAI モデルや重み・閾値などを設定ファイルまたは環境変数で調整可能にする。
- jquants_client の抽象化／モック実装の提供で ETL のユニットテスト容易性を向上。
- ai モジュールのレスポンス検証を強化する（スキーマ確認・詳細なログ出力）。
- DuckDB スキーマ定義・マイグレーション管理を整備し、スキーマ依存の安全性を高める。

--- 

（この CHANGELOG はコードベースのコメント・実装内容から推測して作成しています。実際のコミット履歴が存在する場合はそれに基づく正式な履歴の追記を推奨します。）