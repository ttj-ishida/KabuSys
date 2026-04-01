# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。変更ログは後方互換性やリリースの把握に利用してください。

なお、以下の内容はコードベースからの推測に基づき作成しています（実装上の設計意図・挙動・重要な実装上の工夫を抜粋して記載）。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。本リリースはデータ収集・前処理・研究（リサーチ）・AI を組み合わせた日本株向け自動売買（分析）プラットフォームの基盤機能を提供します。

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val フォーマット対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント判定（クォートあり/なしで挙動を分離）
  - 必須項目取得用の _require() を提供（未設定時は ValueError）。
  - 各種設定プロパティを用意（J-Quants, kabuステーション, Slack, DB パス, 監視しきい値, 環境/ログレベル判定等）。

- AI（自然言語処理）機能 (src/kabusys/ai/)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols をまとめて銘柄ごとにニュースを集約し、OpenAI の gpt-4o-mini（JSON mode）でセンチメントを取得。
    - JST 時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換して処理。
    - バッチ処理（1 API コールあたり最大 20 銘柄）とチャンク化。
    - 1 銘柄あたりの記事数・文字数上限（トリム）を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフ。
    - API レスポンスの頑健なバリデーションと JSON 抽出ロジック（前後テキスト混入対応）。
    - DuckDB への冪等書き込み（DELETE → INSERT）と DuckDB 0.10 互換性のための executemany 空チェック。
    - score_news: 成功時は書き込んだ銘柄数を返す。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロセンチメントはニュースタイトルをフィルタ（マクロキーワード）して LLM（gpt-4o-mini）で評価。
    - API エラー時は macro_sentiment=0.0 としてフェイルセーフ挙動。
    - レジームスコアのクリッピング、閾値に応じたラベル付与、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 内部で直接 OpenAI クライアント呼び出しを行い、news_nlp とは個別実装でモジュール結合を避ける設計。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: raw_financials から EPS / ROE を用いて PER, ROE を計算する calc_value を実装。
    - DuckDB 上の SQL とウィンドウ関数を活用し、営業日スキャン範囲バッファ等を考慮した実装。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（任意ホライズンの将来リターンを一度のクエリで取得）。
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関を算出）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - ファクター統計要約: factor_summary（count/mean/std/min/max/median を計算）。
    - pandas 等への依存はなく、標準ライブラリ＋DuckDB クエリで実装。

- データ基盤 (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースでフォールバック（週末: 非営業日）。
    - next/prev_trading_day は最大探索日数の上限を設定して無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間バッチジョブ。バックフィル日数や健全性チェックを実装。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加（取得件数、保存件数、品質チェック結果、エラー等を保持）。
    - ETL の設計方針に沿った差分更新、バックフィル、品質チェックの枠組みを実装。
    - etl.py で ETLResult を再エクスポート。

- パッケージの小分けインターフェース
  - 各サブパッケージ（ai, research, data 等）の __init__.py で主要関数をエクスポート（例: ai.score_news, ai.score_regime, research.*）。

### 変更 (Changed)
- 初期設計段階として以下の設計上の決定・制約を明確化
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接利用しない設計（target_date を引数で受ける）。
  - DuckDB 互換性考慮（executemany の空配列制約、リテラルリストバインドの不安定さへの回避）。
  - OpenAI 呼び出しは JSON mode（厳密 JSON 出力）を前提としたプロンプト設計とレスポンス検証を実装。

### 修正 (Fixed)
- API 呼び出し・パースの堅牢化
  - OpenAI API 呼び出しでのリトライ対象（RateLimitError, APIConnectionError, APITimeoutError, 5xx）を明確化し、指数バックオフを適用。
  - レスポンスの JSON パース失敗時に最外側の {} を抽出して復元を試みるなど、LLM 特有の余計な前後テキスト混入に対する耐性を実装。
  - API エラー時は例外をそのまま上げずに安全にフェイルセーフ（ゼロスコアやスキップ）にフォールバックする箇所を多数追加（処理継続性の向上）。
- DB 書き込みの冪等性とエラーハンドリングを改善
  - market_regime / ai_scores 等への書き込みは BEGIN/DELETE/INSERT/COMMIT のパターンで冪等化。失敗時は ROLLBACK を試み、ROLLBACK 失敗はログ出力して関数外へ例外を伝播。
  - 部分失敗時に既存データを不必要に消さないよう、書き込み対象コードを限定して DELETE → INSERT を行う設計を採用。

### 非互換 (Breaking Changes)
- 初版のため特に過去バージョンとの互換性を考慮した変更履歴はありません。

### 既知の制限 / 注意点
- OpenAI の API キーは api_key 引数または環境変数 OPENAI_API_KEY で与える必要がある（未設定時は ValueError）。
- DuckDB を前提にした実装（型や SQL 構文が DB に依存）。
- ニュース時間ウィンドウは JST ベースで定義され、内部比較には UTC naive datetime を使用。
- 一部の品質チェックや J-Quants クライアント jq 関連の実装はモジュール外部（data.jquants_client）に依存しており、実行時に外部 API との接続が必要。

---

今後の改善候補（想定）
- 単体テスト・統合テスト、モック用のユーティリティ整備（OpenAI / J-Quants のモックを想定）。
- OpenAI 呼び出しロギングの詳細化／トークン使用量計測。
- ai モジュールの並列化・スループット向上（大量銘柄処理時）。
- DuckDB スキーマ定義・マイグレーションの管理機能追加。

(以上)