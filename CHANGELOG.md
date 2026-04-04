# CHANGELOG

すべての注目すべき変更点はここに記録します。  
このファイルは Keep a Changelog に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を導入しました。主な追加機能と設計上の特徴は以下の通りです。

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージの初期実装を追加。version = 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring（トップレベル __all__）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い（クォート内は無視）に対応。
  - OS 環境変数保護（既存キーの上書きを防止する protected セット）を実装。
  - Settings クラスを公開（settings インスタンス）。J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定 等のプロパティを提供。
  - 必須環境変数未設定時は ValueError を発生させる _require を提供。
  - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL のバリデーションを実装。

- AI ニュース解析 (src/kabusys/ai/news_nlp.py, src/kabusys/ai/regime_detector.py)
  - news_nlp.score_news: raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ保存。
    - 処理ウィンドウ: JST ベースで前日 15:00 〜 当日 08:30（UTC に変換して DB と比較）。
    - バッチ処理: 最大 20 銘柄/チャンク、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出・検証（results リスト、code と score 検証）、未知コードは無視、スコアを ±1.0 にクリップ。
    - DB 書き込みは部分失敗に備え code を絞った DELETE → INSERT（冪等性確保）。DuckDB executemany の空リスト制約に配慮。
    - テスト容易性: _call_openai_api をパッチで差し替え可能に実装。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - MA 計算は target_date 未満のデータのみを参照してルックアヘッドバイアスを防止。
    - マクロニュース抽出は news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しに対する再試行とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームは clip 後に閾値で bull / neutral / bear を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理とロールバック処理を実装。

- データ関連 (src/kabusys/data/*)
  - calendar_management:
    - market_calendar を元に営業日判定・探索を行うユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar 未取得時は曜日ベース（土日を休日）でフォールバックする一貫したルールを実装。
    - calendar_update_job: J-Quants API から差分取得（lookahead/backfill/健全性チェック）して market_calendar を冪等更新。jquants_client と連携（fetch/save）。
  - pipeline / ETL:
    - ETLResult データクラスを導入（ETL の集計結果、品質チェック結果、エラー一覧等を保持）。
    - ETL の差分取得・バックフィル・品質チェック・idempotent 保存方針を実装するための土台を用意。
    - data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ・特徴量 (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily を参照）。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（avg）、相対 ATR、20 日平均売買代金、出来高比率などを計算。必要行数未満は None。
    - calc_value: raw_financials から最新の EPS / ROE を取得し PER / ROE を算出（EPS が 0 または欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（営業日数）先のリターンをまとめて取得。horizons の検証あり。
    - calc_ic: factor と将来リターンの Spearman（ランク相関）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクを採る実装（浮動小数誤差対策で round を利用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- DuckDB と互換性への配慮
  - テーブル存在チェックや DuckDB からの date 変換ユーティリティを実装。
  - executemany に空リストを渡せない DuckDB の挙動に対応した条件分岐を導入。

### 改善・設計上の注意点 (Notable Design / Safety)
- ルックアヘッド防止:
  - score_news / score_regime / factor 計算等は内部で datetime.today()/date.today() を直接参照せず、必ず引数の target_date を基準に処理する設計。
- フェイルセーフ性:
  - OpenAI API の失敗は原則スキップして処理継続（多くのケースで 0.0 や空辞書にフォールバック）。ただし DB 書き込み失敗は上位に伝播して明示的にハンドル。
- 冪等性:
  - ETL / calendar / AI 書き込み周りは既存行を削除してから挿入するなどの冪等的な保存手法を採用。
- ロギング:
  - 各処理で詳細な info/debug/warning ログを出力するように実装。
- テスト容易性:
  - OpenAI への呼び出し関数はモジュール内関数を介しており、unit test で差し替え可能。

### 既知の注意点 (Known issues / Constraints)
- OpenAI SDK の例外型や属性（status_code 等）に合わせた安全な取り扱いを行っているが、将来の SDK 変更に注意が必要。
- 一部の外部依存（jquants_client や DB スキーマ）は本リリースに含まれないため、連携先の実装／テーブル定義が必要。
- DuckDB のバージョン差異により list 型バインド等で挙動差があり得るため、executemany を利用する箇所で互換性対策を実施済み。

### セキュリティ (Security)
- API キーやパスワードは環境変数から取得し、未設定時は明示的にエラーを出す（漏洩防止は利用者の運用に依存）。

---

貢献・修正履歴は今後のリリースで追記します。もしこのCHANGELOGの文言（表現）や記載粒度について希望があればお知らせください。