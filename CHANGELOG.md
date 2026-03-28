Keep a Changelog
================

すべての重要な変更点をこのファイルに記録します。本プロジェクトでは "Keep a Changelog" の形式に従います。

0.1.0 - 2026-03-28
------------------

初期リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。
主にデータ取得・ETL・カレンダ管理・リサーチ・AIによるニュース解析・市場レジーム判定・設定管理の各モジュールを含みます。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン定義: __version__ = "0.1.0"。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 高度な .env パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - Settings クラスで主要設定をプロパティとして提供:
    - J-Quants / kabu API / Slack / DB パス (duckdb, sqlite) / 環境 (development/paper_trading/live) / ログレベル 等。
  - 必須環境変数の取得で未設定時は ValueError を発行する _require() を導入。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを導入。ETLの取得数、保存数、品質チェック結果、エラー情報を保持。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント経由）。
    - DuckDB のテーブル最終日取得ユーティリティ、テーブル存在チェック等を実装。
    - DuckDB バインドの互換性考慮（executemany に対して空リストを送らないガード）。
  - ETL の公開インターフェースを etl モジュール経由で再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの夜間差分更新ジョブ (calendar_update_job) を実装。
    - 営業日判定・次/前 営業日取得・期間内営業日取得・SQ日判定等のユーティリティを提供。
    - DB にデータがない場合は曜日ベースのフォールバックを使用。
    - バックフィル・健全性チェック（将来日付の異常検知）を実装。
    - J-Quants クライアント経由での取得/保存を想定。

- リサーチ (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m/mom_3m/mom_6m、200日移動平均乖離 (ma200_dev) を計算する calc_momentum を実装。
    - ボラティリティ/流動性: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - バリュー: PER、ROE を計算する calc_value を実装（raw_financials と prices_daily を組合せ）。
    - DuckDB SQL を用いた計算で、データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関、必要最小サンプル数検査）。
    - ランキング補助: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - zscore_normalize を外部データモジュールから再エクスポート。

- AI モジュール (kabusys.ai)
  - ニュースNLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメントを算出する score_news を実装。
    - JST ベースのニュースウィンドウ（前日15:00〜当日08:30）を計算する calc_news_window を提供。
    - 1銘柄あたりの最大記事数・最大文字数でトリムしてトークン肥大化に対応。
    - JSON Mode 出力の厳密バリデーション（results リスト、code/score）およびパース失敗時の補正（最外の {} 抽出）を実装。
    - API レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時はスキップして継続（フォールバック）。
    - スコアは ±1.0 にクリップして保存。部分失敗時に既存スコアを保護するため、書き込みは対象コードのみ DELETE→INSERT する。
    - テスト容易性のため _call_openai_api をモック可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して日次で market_regime テーブルに書き込む score_regime を実装。
    - マクロキーワードで raw_news をフィルタし、LLM（gpt-4o-mini）へ送信して macro_sentiment を算出。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0。
    - API 呼び出しはリトライ・バックオフを行い、全リトライ消費時は 0.0 にフォールバックする堅牢な設計。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行い、失敗時は ROLLBACK を試行。
    - テスト用に _call_openai_api を差し替え可能。

Changed
- （初期リリースのため変更履歴はありません）

Fixed
- （初期リリースのため修正履歴はありません）

Security
- 設定管理で OS 環境変数を保護する仕組みを導入（.env の読み込みで既存の OS 環境変数を保護する protected セットを使用）。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に渡す方式。未設定時は ValueError を投げるため動作ミスを検出しやすい。

Notes / Design decisions
- ルックアヘッドバイアス防止: score_news / score_regime 等の AI・調査処理は内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計。
- DuckDB 互換性: executemany に空リストを渡すと失敗する環境を考慮して、空チェックを行ってから executemany を呼ぶ実装を採用。
- フェイルセーフ: OpenAI API の失敗やレスポンスパース失敗は例外で全処理を止めず、警告ログを残して中立値（0.0）やスキップを行うポリシー。
- テスト支援: AI モジュールの API 呼び出し部分はモック可能にしてユニットテスト容易性を確保。
- ログ出力: 各処理に対して INFO/DEBUG/WARNING/EXCEPTION ログを適切に配置。

Known limitations / TODO
- PBR・配当利回り等、いくつかのバリューファクターは未実装（calc_value の注記参照）。
- strategy / execution / monitoring パッケージの実装詳細は初期リリースでは公開インターフェースのみ想定（個別の注文ロジック等は別途実装予定）。
- OpenAI モデル名は gpt-4o-mini がハードコーディングされているため、将来的に設定化やモデル切替を検討。

ライセンスや貢献方法などは別ファイル（LICENSE / CONTRIBUTING）を参照してください。