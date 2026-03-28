# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリースポリシー: 互換性のある変更はメジャー/マイナー/パッチで管理します（本リポジトリは初期公開版を記録しています）。
- 日付はリリース日を示します。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買プラットフォームの基盤機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを追加（__version__ = 0.1.0、公開モジュールを __all__ で定義）。
- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準に探索、CWD 非依存）。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルの堅牢なパーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、行内コメント処理）。
  - 環境変数の必須取得ユーティリティ _require と Settings クラスを追加。J-Quants、kabuステーション、Slack、DB パス、実行環境（development/paper_trading/live）やログレベルの検証を提供。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを生成。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1リクエスト最大 20 銘柄）と JSON Mode を利用したレスポンス検証を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。API 失敗時は部分スキップで堅牢に継続。
    - レスポンスバリデーション（JSON 抽出・results 構造・code 照合・スコア数値化）と ±1.0 クリッピング。
    - ai_scores テーブルへの冪等的な更新（DELETE→INSERT、部分失敗時に他コードを保持する実装）。
    - calc_news_window（ニュース収集ウィンドウ計算）と score_news API を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ/フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。
    - ルックアヘッドバイアス回避設計（内部で datetime.today()/date.today() を参照しない、DB クエリに date < target_date を使用）。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録データ優先、未登録日は曜日ベースのフォールバックを行う一貫したロジックを実装。
    - JPX カレンダー夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETL 用ユーティリティと ETLResult データクラスを実装（取得/保存件数、品質問題、エラーの集約）。
    - 差分更新（最終取得日ベース）、バックフィル、idempotent な保存（jquants_client.save_* を利用）および品質チェックの扱い方針を定義。
    - DuckDB を想定した最大日付取得やテーブル存在チェックなどのヘルパーを実装。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、バリュー（PER, ROE）を計算する calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照。
    - データ不足時の None 扱い等を明確にし、結果は (date, code) ベースの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、SQL で一括取得）。
    - IC（Spearman のランク相関）を計算する calc_ic、ランキングユーティリティ rank、統計サマリー factor_summary を実装。
- 共通設計方針（ドキュメント化・実装）
  - ルックアヘッドバイアス回避（内部で現在時刻を直接参照しない設計を徹底）。
  - OpenAI 呼び出しは各モジュールで独立したプライベート関数として実装し、テスト容易性のため patch による差し替えを想定。
  - DuckDB における実装上の互換性（executemany に空リストを渡さない等）に配慮した実装。
  - トランザクション／ROLLBACK の扱いを明確化し、ROLLBACK 失敗時は警告ログを出す実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env 読み込みでのエッジケースを改善
  - export プレフィックスやクォート内のバックスラッシュエスケープ、行内コメント解釈などを正しく処理するようにした。
- OpenAI 結果パースでの堅牢性向上
  - JSON モードでも前後に余計なテキストが混ざるケースに対して最外の JSON オブジェクトを抽出してパースすることでスキップ率を低減。

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト性向上）であり、環境変数 OPENAI_API_KEY をデフォルトで参照。機密情報の取り扱いは Settings 経由で明示。

---

注:
- 本 CHANGELOG はソースコードの実装内容から推測してまとめたもので、実際の開発履歴やコミットログに基づくものではありません。実装意図や設計方針、主要な公開 API を中心に記載しています。