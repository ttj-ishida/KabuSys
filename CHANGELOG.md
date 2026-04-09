# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
このプロジェクトの初期リリースとして、以下はソースコードから推測して作成した 変更履歴 です。

また、日付は本ファイル作成日時（2026-04-09）を用いています。実際の公開日が異なる場合は適宜更新してください。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-09

### Added
- パッケージ初期リリース ("KabuSys - 日本株自動売買システム")。バージョンは 0.1.0 に設定。
- モジュール公開:
  - kabusys パッケージの公開サブモジュール: data, strategy, execution, monitoring。
- 環境設定管理:
  - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パースロジック（export prefix、クォート内エスケープ、インラインコメント取り扱い等）を実装。
  - 環境変数保護（OS 環境変数を protected set として上書き防止）に対応。
  - Settings クラスに各種設定プロパティを追加（J-Quants / kabu API / LINE / DB パス / paper trading 等）。
  - 環境変数検証: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェックとエラーメッセージ。

- AI（OpenAI）関連機能:
  - news_nlp モジュール:
    - raw_news と news_symbols を用いて銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini）でセンチメント評価（score_news）。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数トリム）、JSON モード使用。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーション（results 配列、code/score 検証）、スコアを ±1.0 にクリップ。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - calc_news_window ヘルパー（JST でのニュース収集ウィンドウ -> UTC naive datetime を返す）。
    - テスト容易性のため OpenAI 呼び出し点（_call_openai_api）を差し替え可能に設計。

  - regime_detector モジュール:
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム ('bull'/'neutral'/'bear') を判定（score_regime）。
    - MA 計算は target_date 未満のデータのみを参照し、ルックアヘッドバイアスを排除。
    - マクロニュース抽出（マクロキーワードでフィルタ、最大記事数制限）→ OpenAI で JSON 出力をパースして macro_sentiment を取得。
    - API 障害時のフェイルセーフ: macro_sentiment を 0.0 にフォールバックして処理継続。
    - データは market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Data（データ基盤）機能:
  - data.pipeline:
    - ETL パイプラインインターフェースと ETLResult データクラスを提供（取得数/保存数/品質問題/エラー等を集約）。
    - 差分更新、バックフィル、品質チェックを想定（設計文書に基づく実装方針）。
  - data.etl:
    - ETLResult を再エクスポート（外部利用向け）。
  - data.calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブルの夜間バッチ更新 calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末除外）。
    - API からの取得は差分取得・バックフィル（直近数日再フェッチ）・健全性チェックを実装。
    - J-Quants クライアント経由で取得/保存（jq.fetch_market_calendar / jq.save_market_calendar を想定）。

- Research（リサーチ）機能:
  - research.factor_research:
    - モメンタム、バリュー、ボラティリティ/流動性の計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - calc_value: PER（株価/EPS）、ROE（最新財務データを参照）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比など。
    - DuckDB SQL を用いた一括計算でパフォーマンスを重視、欠損時の None 扱い。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満で None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージの __all__ に主要関数を再公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意:
  - 必須キー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）未設定時は明示的に ValueError を送出する箇所あり。
  - .env 自動ロード時に既存 OS 環境変数を保護する仕組みを導入。
  - API キー等の管理は .env or 環境変数で行う想定（README 等で利用上の注意を記載推奨）。

### Notes / Implementation details（設計上の重要点）
- ルックアヘッドバイアス対策:
  - AI スコアリング / レジーム判定 / ファクター計算は target_date ベースで過去データのみを参照するよう設計。
  - datetime.today()/date.today() を直接参照しない実装方針が明示されている箇所あり。
- OpenAI 呼び出し:
  - gpt-4o-mini モデルを利用（JSON モードを期待）。
  - レスポンスの堅牢なパースと部分失敗時のフェイルセーフ（スコア 0.0 またはスキップ）を実装。
  - テスト容易性のため _call_openai_api を差し替え可能。
- DuckDB 互換性:
  - executemany へ空リストを渡さない等、DuckDB バージョン間の差異に配慮した実装。
- ロギング:
  - 多数の場所で情報・警告・例外ログを出力するよう実装（運用時の監視に有用）。

---

既知の改善余地（将来的な TODO / 注意点）
- news_nlp / regime_detector の OpenAI 呼び出しに関するレート管理・コスト最適化のさらなる改善。
- ETL パイプラインの詳細（quality モジュールの実装、jquants_client の具体実装）は外部モジュール依存のため実装状況に応じて更新が必要。
- 単体テスト・統合テストの追加（特に外部 API 呼び出しをモックするテスト）。

---

作成: KabuSys 開発チーム（コードベースから自動生成した推測 CHANGELOG）