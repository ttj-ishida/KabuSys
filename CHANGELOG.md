# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
慣例: 重要な変更は "Added / Changed / Fixed / Deprecated / Removed / Security" に分類しています。

[Unreleased]
- （なし）

## 0.1.0 - 2026-04-01

初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（src/kabusys/__init__.py）。
  - バージョン番号を 0.1.0 に設定。

- 設定管理
  - 環境変数 / .env 自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメントを正しく処理。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル等をプロパティとして取得可能。
    - env 検証（development / paper_trading / live）やログレベル検証を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- AI モジュール
  - ニュース NLP（銘柄ごとのニュースセンチメント集計）機能を追加（src/kabusys/ai/news_nlp.py）。
    - raw_news, news_symbols を集約して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信し、ai_scores テーブルへ書き込み。
    - チャンク毎処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数 & 文字数トリム、JSON バリデーション、スコアクリップ（±1.0）、部分書換え（DELETE → INSERT）による冪等性を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。
    - テスト用に OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window(target_date) ユーティリティを提供（JST ベースのニュース収集ウィンドウ計算）。
    - 公開関数: score_news(conn, target_date, api_key=None) — 成功時は書き込んだ銘柄数を返す。

  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、冪等な DB 書き込みを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時は 1 を返す。

- Research（リサーチ）モジュール
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算を実装（src/kabusys/research/factor_research.py）。
    - calc_momentum, calc_volatility, calc_value を提供。prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。
    - 不足データ時は None を返す等の頑健な振る舞いを実装。
  - feature_exploration: 将来リターン, IC 計算, ランク変換, 統計サマリーを実装（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns（任意ホライズン対応）、calc_ic（スピアマンρ）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
  - research パッケージの公開 API を __init__ で整理して再公開。

- Data（データプラットフォーム）モジュール
  - カレンダー管理（market_calendar）を実装（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定API。
    - DB に未登録日は曜日ベースでフォールバックするロジック。最大探索日数を設定して無限ループを防止。
    - calendar_update_job により J-Quants から差分取得して冪等に保存（バックフィルや健全性チェック含む）。
  - ETL パイプラインの基礎（src/kabusys/data/pipeline.py）。
    - ETLResult データクラスを定義（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得 / 保存 / 品質チェックの設計方針を反映。
  - etl.py で ETLResult を再エクスポート。

- DuckDB を主要な内部ストレージ向けに標準採用。多くの関数が DuckDB 接続オブジェクトを引数に取り SQL と組み合わせて処理する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パースの堅牢化（クォート内のエスケープ、export プレフィックス、インラインコメント取り扱い等）により実運用での環境変数ロードの信頼性を向上。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能（テスト容易化および環境変数漏洩リスク緩和）。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト / セキュリティ用途）。

---

注記（設計上の重要点）
- ルックアヘッドバイアス防止: 多くの関数は datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に受け取る設計になっています。
- フェイルセーフ: 外部 API （OpenAI / J-Quants）呼び出し失敗時は例外を無理に伝播させずフォールバック（ゼロスコア等）して処理を継続する戦略を採用。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を確保。
- テスト容易性: OpenAI 呼び出しの内部関数は差し替え可能に設計（unit test 用の patch を想定）。
- DuckDB の executemany 周りの互換性に配慮（空リストバインドの回避）した実装。

今後の予定（例）
- 監視・実行モジュール（execution / monitoring）の詳細実装と自動売買フローの追加。
- ドキュメント（API リファレンス、運用手順、データスキーマ）とサンプル ETL ジョブの拡充。