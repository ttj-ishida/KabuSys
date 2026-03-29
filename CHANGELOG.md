# CHANGELOG

すべての重要な変更履歴を記録します。本稿は Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-29
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期公開。パッケージのトップレベルで以下モジュールを公開するように設定：
    - data, strategy, execution, monitoring（__init__.py の __all__ にて公開）
  - パッケージバージョン: 0.1.0

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルートの自動検出: .git または pyproject.toml を起点に探索して .env / .env.local を読み込む実装を追加（CWD に依存しない）。
  - .env パーサ実装:
    - コメント行、空行、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。クォート外の `#` は直前が空白/タブのときのみコメント扱い。
  - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを抑制可能。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護するための protected キーの概念を導入。
  - 必須設定取得ヘルパー `_require` と、各種設定プロパティ（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル など）を提供。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値を検証して不正値は ValueError。

- データ関連 (`kabusys.data`)
  - カレンダー管理 (`data/calendar_management.py`)
    - JPX マーケットカレンダーを扱うユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースのフォールバック（週末除外）を実装。
    - DB の部分登録（まばら）でも一貫した判定を返す設計。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装。J-Quants クライアント経由で差分取得 → 冪等保存（save 側に委譲）し、バックフィルと健全性チェックを実施。
  - ETL パイプライン (`data/pipeline.py`, `data/etl.py`)
    - ETLResult dataclass を追加（取得件数・保存件数・品質問題・エラー一覧 等を保持）。
    - 差分取得・バックフィル・品質チェック方針を反映したユーティリティ実装。
    - DuckDB の存在チェックや最大日付取得など内部ヘルパーを実装。
    - `etl` モジュールで ETLResult を公開エクスポート。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`research/factor_research.py`)
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離）を計算する `calc_momentum` を実装。
    - ボラティリティ／流動性: 20日 ATR, ATR/close, 平均売買代金, 出来高比率 を計算する `calc_volatility` を実装。
    - バリュー: PER, ROE を raw_financials と prices_daily から計算する `calc_value` を実装（最新財務レコード取得ロジック含む）。
    - いずれも DuckDB 接続を受け取り SQL で計算する設計（本番オーダーAPIへのアクセスなし）。
  - 特徴量探索 (`research/feature_exploration.py`)
    - 将来リターン計算 `calc_forward_returns`（任意のホライズンに対して LEAD を使い一括取得）。
    - IC 計算（Spearman の ρ 相当）`calc_ic` とランキングユーティリティ `rank`。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - データ統計ユーティリティの再エクスポート: `zscore_normalize`（kabusys.data.stats 由来）を __all__ に含めて公開。

- AI / NLP モジュール (`kabusys.ai`)
  - ニュースセンチメントスコア (`ai/news_nlp.py`)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをバッチ（最大 20 銘柄/チャンク）で OpenAI（gpt-4o-mini）に投げてセンチメントスコアを算出して ai_scores に書き込む `score_news` を実装。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換する `calc_news_window` を実装。
    - 1 銘柄あたりの記事数上限 / 文字数上限によるトリム処理、JSON モード応答のバリデーション、スコアの ±1.0 クリップを実装。
    - API 呼び出しのリトライ（429 / 接続断 / タイムアウト / 5xx）を指数バックオフで実施。部分失敗に備え、DB 書き込みは取得できたコードのみ置換（DELETE→INSERT：部分失敗時に既存データを保護）。
    - レスポンスパース失敗時はログを出して当該チャンクをスキップ（フェイルセーフ）。
  - 市場レジーム判定 (`ai/regime_detector.py`)
    - ETF 1321（日経225 連動 ETF）について 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次の market_regime を算出する `score_regime` を実装。
    - マクロニュース抽出は `news_nlp.calc_news_window` を利用、取得タイトルを LLM に与えて JSON（{"macro_sentiment": float}）で返すようプロンプトを設計。
    - LLM 呼び出しは独立実装（news_nlp と共有しない）で、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ動作。
    - 計算結果は冪等に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- 環境設定:
  - OS 環境変数を protected として .env による上書きを防止する仕組みを導入。自動.env 読み込みは環境変数で無効化可能。
- OpenAI API キー:
  - OpenAI キーが未設定の場合は明示的に ValueError を投げ、呼び出し側に設定を促す（score_news / score_regime）。

### 注意事項 / 実装上の設計判断 (Notes)
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定のすべての関数は datetime.today()/date.today() を内部で参照しない（外部から target_date を与える設計）。prices_daily クエリでも target_date 未満等の排他条件を採用。
- DuckDB 依存:
  - 多くの処理は DuckDB 接続を前提としており、executemany に空リストを与えられないバージョン（DuckDB 0.10 等）への互換性を考慮したガードを追加。
- 外部モジュール依存:
  - J-Quants クライアント（kabusys.data.jquants_client）、OpenAI SDK、DuckDB 等の外部依存が必要。
- フェイルセーフ:
  - LLM 失敗時はゼロや中立値にフォールバックして処理を継続する実装が多数（運用時の堅牢性を優先）。
- API 呼び出しのテスト容易性:
  - OpenAI 呼び出し部分は内部でラップされており、ユニットテスト時には差し替え（patch）可能な設計。
- 公開 API:
  - ETLResult の to_dict により監査ログ出力や外部監視に使いやすくしている。

### 既知の制約 / 今後の作業 (Known issues / TODO)
- strategy / execution / monitoring モジュールはトップレベルで公開対象になっているが、本リリースではここに含まれる具体的な実装（発注ロジック等）は提供されていない場合があります。運用上の発注機能は別途実装・レビューが必要です。
- OpenAI を利用する箇所はコストとレイテンシに注意して運用する必要あり（バッチサイズやリトライ設定は現状のデフォルトに依存）。
- J-Quants からのデータ取得・保存ロジック（jquants_client）の実装と運用テストが必要。

---
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は、リリース管理者による確認・補完を推奨します。