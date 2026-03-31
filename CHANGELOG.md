# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従って管理しています。

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能と内部設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, research, ai, config, 等のサブモジュールを提供。
  - バージョン管理: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装（プロジェクトルートの自動検出、.env → .env.local の優先度）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどに対応）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（J-Quants・kabu API・Slack・データベースパス・監視閾値・環境検証など）。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティを実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング: score_news を実装（gpt-4o-mini の JSON mode を利用）。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、銘柄ごとにスコアを付与。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム、レスポンスバリデーション（JSON 抽出・results リスト・コード照合・スコア数値検証）。
    - API エラー（429/ネットワーク/タイムアウト/5xx）への指数バックオフリトライを実装。失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB へ冪等的に書き込むロジック（DELETE → INSERT、executemany 前の空リストチェックを含む）。
  - 市場レジーム判定: regime_detector モジュールを実装（ETF 1321 の 200 日 MA 乖離とマクロニュース LLM センチメントを合成）。
    - ma200_ratio の算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードでニュースを抽出し、OpenAI によるマクロセンチメント評価（JSON 応答のパース・リトライ・フェイルセーフ実装）。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入対応（引数 or 環境変数 OPENAI_API_KEY）。

- データ関連 (kabusys.data)
  - calendar_management: JPX カレンダー管理と営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の際は曜日ベース（土日非営業）でのフォールバックを行う堅牢な実装。
    - calendar_update_job: J-Quants からの差分取得と market_calendar テーブルへ冪等保存、バックフィルや健全性チェックを実装。
  - ETL パイプライン (pipeline.py)
    - ETLResult データクラスを追加（実行結果の構造化・品質問題一覧・シリアライズ to_dict を含む）。
    - 差分更新・バックフィル・品質チェックの方針を実装するためのユーティリティ関数を提供（テーブル存在確認、最大日付取得など）。
  - etl.py で ETLResult を再エクスポート。

- リサーチ・ファクター分析 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出（target_date 以前の最新財務データを利用）。
    - DuckDB SQL を利用した高効率実装、データ不足時の None ハンドリング。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算。入力検証（horizons の上限・正値）を実施。
    - calc_ic: スピアマンランク相関（IC）計算（code での結合・None/非有限値除外・サンプル数チェック）。
    - rank: 同順位は平均ランクにするランク関数（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。

### Changed
- 初期設計段階で下記の設計方針を明文化・実装に反映
  - ルックアヘッドバイアス回避: 各処理は内部で datetime.today()/date.today() を直接参照せず、target_date を引数として受け取る設計。
  - DB 書き込みは冪等性を重視（DELETE → INSERT, ON CONFLICT など）し、部分失敗時に既存データを保護する実装。
  - OpenAI との統合は JSON mode を使い、レスポンスの堅牢なパースとフェイルセーフな復帰を行う。

### Fixed / Robustness improvements
- .env パーサの強化: export 句、クォート内のバックスラッシュエスケープ、行内コメントの扱いを考慮。
- OpenAI 呼び出し周りの堅牢化: RateLimit/ネットワーク/タイムアウト/5xx に対するリトライとエラーハンドリング（警告ログ・フォールバックスコア）。
- DuckDB 対応上の注意点を考慮:
  - executemany に空リストを渡さないよう保護（DuckDB 0.10 の制約回避）。
  - 日付値の型変換ユーティリティを追加（DuckDB の日付表現への互換性確保）。
- news_nlp / regime_detector での JSON パース時に余分な前後テキストが混入するケースへの対処（最外側の {} を抽出してパースを試行）。

### Known issues / Notes
- ETL pipeline の一部のユーティリティ（ファイル末尾の未完成箇所など）は現行スニペットにおいて途中で切れている箇所があるため、実運用前に該当箇所の最終レビューが必要です（リリース後の小修正予定）。
- ai パッケージの __init__ では score_news を明示的に公開。regime_detector はモジュールとして存在するが、必要に応じてトップレベル export を追加することを検討。

---

（以降のリリースでは Unreleased セクションを先頭に追加し、変更を逐次記録します。）