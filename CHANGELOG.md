# Changelog

すべての注目すべき変更をここに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。バージョン番号はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

初期リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは 0.1.0。
  - パッケージ公開 API: __all__ に ["data", "strategy", "execution", "monitoring"] を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の自動ローディング機能を提供（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパース強化:
    - コメント / 空行無視、export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント認識の改善。
  - .env 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリケーションで使用する各種設定値（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル判定 など）をプロパティ経由で取得可能。
  - 必須設定未存在時は ValueError を送出する _require を実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを計算。
    - バッチ処理（デフォルト 20 銘柄/チャンク）、1銘柄あたり記事トリム（記事数上限・文字数上限）を実装。
    - 再試行・バックオフロジック（429, ネットワークエラー, タイムアウト, 5xx）を実装。
    - レスポンスの厳密検証（JSON 抽出、results 配列検証、コード照合、数値チェック）、スコア ±1.0 でクリップ。
    - 書き込みは部分失敗に強い設計（取得できたコードだけを DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し箇所は patch 可能な _call_openai_api を利用。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日 MA 乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - ニュースフィルタはマクロキーワードリストを使用し、最大記事数制限あり。
    - OpenAI 呼び出しは独立実装（news_nlp と意図的に分離）。
    - API エラー時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）にて処理。

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定ロジックを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録データを優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - カレンダー夜間バッチ更新 job (calendar_update_job) を実装（J-Quants から差分取得 → 保存、バックフィル、健全性チェック）。
    - 最大探索範囲やバックフィル、将来日付の健全性チェック等の安全策を実装。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（pipeline.ETLResult をデータエクスポート）。
    - ETL の差分取得・保存・品質チェックを想定したインターフェースとユーティリティを用意。
    - DuckDB に対するテーブル存在チェックや max date 取得ユーティリティを実装。

- 研究用 / リサーチ機能 (kabusys.research)
  - ファクター計算 (research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を計算する関数群を追加: calc_momentum, calc_value, calc_volatility。
    - DuckDB SQL を用いた実装（prices_daily, raw_financials のみ参照）。不足データ時は None を返す設計。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（calc_forward_returns：柔軟なホライズン対応）、IC 計算（スピアマンのρ）、ランク付けユーティリティ、統計サマリー（factor_summary）を実装。
    - 外部依存を持たない（標準ライブラリのみ）設計。

### 変更 (Changed)
- 全体的な設計方針の明文化
  - ルックアヘッドバイアスを避けるため、datetime.today() / date.today() を主要なスコアリング・解析ロジックで直接参照しない実装方針を採用（すべて target_date 引数駆動）。
  - DuckDB 互換性考慮（executemany の空リスト制約への対応など）。

- OpenAI 関連
  - gpt-4o-mini をデフォルトモデルとして採用、JSON Mode を使った厳格なレスポンス設計。
  - API 呼び出し箇所に再試行・指数バックオフ・5xx と 4xx の扱い差分などの堅牢化処理を実装。

### 修正 (Fixed)
- DB 書き込み時のトランザクション保護
  - 各種書込処理で BEGIN/COMMIT/ROLLBACK を適用し、ROLLBACK に失敗した場合に警告ログを出すようにして堅牢性を向上。

### 注意事項 / 動作仕様 (Notes)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要があり、未設定時は ValueError が発生します（news_nlp.score_news, regime_detector.score_regime）。
- OpenAI 呼び出しで致命的な失敗が発生した場合でも、フェイルセーフとしてゼロ相当（中立）で継続する箇所が多く、システム全体の頑健性を優先しています。
- ai モジュールはテスト容易性を考慮して内部の _call_openai_api をモック可能に実装しています。
- DuckDB を前提としており、日付や時間は明示的に date / datetime オブジェクト（UTC naive など）で扱うよう注意されています。
- news_nlp の時間ウィンドウは JST ベースで定義され、内部では UTC naive datetime に変換して DB クエリに用いる設計です（calc_news_window を参照）。

### 既知の制限 (Known limitations)
- PBR や配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- ETL の具体的な J-Quants クライアント実装（jquants_client）の詳細は別モジュールに依存しており、実行には外部 API アクセスが必要。

---

今後のリリースでは以下を想定しています（例）:
- strategy / execution / monitoring モジュールの具現化（実取引ロジック・発注、安全装置）
- 追加のファクターやポートフォリオ構築ユーティリティ
- 性能最適化・大規模データ対応、より詳細な品質チェックルールの実装

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する際は、変更の意図や反映状況を開発チームでご確認ください。）