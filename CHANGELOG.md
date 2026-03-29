# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このリポジトリのバージョン番号は `src/kabusys/__init__.py` の `__version__` に従います。

## [Unreleased]
今後のリリースに向けた変更はここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを定義（kabusys v0.1.0）。__all__ に data, strategy, execution, monitoring を公開。
- 環境設定 (kabusys.config)
  - 環境変数/設定読み込みモジュールを追加。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動でルートを特定する機能を実装し、CWD に依存しない自動 .env ロードを提供。
  - .env パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - .env と .env.local の読み込み優先順位を実装（OS 環境変数を保護する protected 機能を含む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
  - Settings クラスを追加し、型安全なプロパティ経由で以下を取得可能に:
    - J-Quants, kabuステーション, Slack, DB パスなどの設定
    - env（development / paper_trading / live）と log_level のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時に明確なエラーを投げる `_require` 実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp.py)
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を用いて各銘柄のセンチメントを -1.0〜1.0 で評価する機能を追加。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST = UTC で前日 06:00 ～ 23:30）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄／リクエスト）、記事トリム（件数・文字数制限）、JSON Mode 応答の妥当性検証、スコアクリップ、部分成功時の DB 置換（DELETE → INSERT）ロジックを実装。
    - API 呼び出しでのリトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。失敗時はスキップしてフェイルセーフに継続。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に（モジュール内部でラップ）。
  - マーケットレジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - prices_daily / raw_news を参照し、ma200_ratio 計算、マクロ記事抽出、OpenAI によるマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライ、JSON パースの堅牢化を実装。
    - モジュール間の結合を避けるため、OpenAI 呼び出しは news_nlp と独立した実装。
- データ処理 (kabusys.data)
  - カレンダー管理 (calendar_management.py)
    - JPX 市場カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得して market_calendar テーブルへ冪等更新（ON CONFLICT 相当）する。
    - 営業日判定ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合の曜日ベースフォールバック、探索上限の導入、健全性チェック、バックフィルロジックを実装。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを追加し、ETL の各種カウント、品質検査結果、エラー情報を構造化して返却可能に。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティ関数を実装。
    - etl.py で pipeline.ETLResult を再エクスポート。
- リサーチ / ファクター (kabusys.research)
  - factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）などのファクター計算を実装。prices_daily / raw_financials のみを参照する安全な実装。
    - DuckDB を使ったウィンドウ関数で効率的に計算し、結果を (date, code) をキーとした dict のリストで返す。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンをまとめて取得可能。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を落とし込み、必要件数が不足する場合は None を返す堅牢な実装。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで処理し、浮動小数の丸めで ties 判定の安定化を実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの __all__ を整備し、主要 API を再エクスポート。
- その他
  - 各モジュール共通の設計方針を文書化（ルックアヘッドバイアス回避のため date/datetime の直接参照を避ける、DuckDB 使用、外部依存を最小限にする等）。
  - ロギングの導入と処理状況・警告の明示的出力。

### 変更 (Changed)
- なし（初回リリースのため後続で記録予定）。

### 修正 (Fixed)
- なし（初回リリースのため後続で記録予定）。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- 環境変数自動ロード時に OS 環境変数を保護する処理を追加（.env の読み込みで既存のシステム環境変数を上書きしないよう保護セットを使用）。

---

注:
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（引数または環境変数 OPENAI_API_KEY）が必要です。未設定時は ValueError を送出します。
- DuckDB を前提として設計されています。DB スキーマ（prices_daily, raw_news, market_calendar, raw_financials, news_symbols, ai_scores, market_regime など）に依存します。
- 初回リリースでは主にデータ収集・加工・研究向けの基盤機能および AI を使ったスコアリング・判定ロジックを実装しています。実運用時の発注・実行ロジック（execution 等）は別モジュールで切り分けられています。