# Changelog

すべての重要な変更点を記録します。This project adheres to "Keep a Changelog"（日本語訳で整理）。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-04
初回公開リリース

### 追加 (Added)
- パッケージの初期エントリポイントを追加
  - pakage: `kabusys`、バージョン `0.1.0` を設定（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring モジュール名を公開。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む機能。
  - .env パーサの実装: コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント（クォートの有無で挙動が異なる）に対応。
  - 自動ロードの無効化オプション: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数保護: .env の読み込みで既存の OS 環境変数を保護する仕組み（.env.local は上書き可能だが保護対象キーは上書きされない）。
  - Settings クラスを提供（settings インスタンスを公開）。J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境（development/paper_trading/live）などの設定取得メソッドを実装。
  - 必須値未設定時は明示的な ValueError を投げる `_require` を提供。

- AI 関連モジュールを追加（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - ニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window`。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄／回）、JSON Mode を想定した応答パース、レスポンスのバリデーション、スコア ±1.0 にクリップ。
    - リトライ戦略（429／ネットワーク断／タイムアウト／5xx）を実装（指数バックオフ、最大リトライ回数設定）。
    - DuckDB の executemany の制約に配慮して、部分的に DELETE → INSERT により idempotent に ai_scores テーブルを更新。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（ユニットテストで patch 可能な内部関数）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で market_regime を算出。
    - マクロ記事はキーワードベースで抽出し、LLM（gpt-4o-mini）へ渡す。レスポンスパース失敗や API エラーは macro_sentiment=0.0 としてフェイルセーフ動作。
    - 結果は idempotent に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）、DB 書き込み失敗時は ROLLBACK を試行。
    - API 呼び出し時のリトライ/バックオフ処理を実装。

- Data モジュールを追加（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar テーブル）を管理するユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に値がない場合には曜日ベース（土日除外）のフォールバックを提供。部分的なデータ（まばらな DB）でも一貫した判定を返す設計。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル機能、健全性チェック）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL の取得数・保存数・品質チェック結果・エラー要約などを保持）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client, quality との連携を前提）。
    - etl モジュールから ETLResult を再エクスポート。

- Research モジュールを追加（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、ma200 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER, ROE）などの計算関数を実装。DuckDB SQL と Python を組合せて計算。
    - データ不足時の扱い（条件を満たさない場合は None）や、戻り値は (date, code) をキーにした辞書リスト形式。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: horizons バリデーション（1〜252）、単一クエリで最適化して取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装し、サンプル数不足時は None を返す。
    - ランク関数（rank）は同順位の平均ランクを適切に扱う（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計ユーティリティ。
  - research パッケージの __all__ で主要関数を公開。

### 変更 (Changed)
- （初版のため履歴なし）

### 修正 (Fixed)
- （初版のため履歴なし）

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。ただし以下は利用側で注意が必要:
  - OpenAI API キー（OPENAI_API_KEY または各関数の api_key 引数）が未設定の場合、score_news / score_regime は ValueError を送出する設計。
  - .env の自動読み込みを無効化しない限り、パッケージ初期化時にプロジェクトルートが検出されれば .env / .env.local が読み込まれます。テスト環境などで影響がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - DuckDB の executemany に関するバージョン差異に対する対策を実装しているが、使用する DuckDB バージョンによっては挙動に差異が出る可能性あり（空リストの executemany は回避済み）。

### セキュリティについて (Security)
- API キー等のシークレットは環境変数で取得する設計。リポジトリに機密情報や .env を含めないでください。
- .env の上書きポリシーは OS 環境変数を保護するように設計されていますが、.env.local は上書き用に優先して読み込まれます。

### 実装上の設計方針（主要ポイント）
- ルックアヘッドバイアスを避けるため、内部処理で datetime.today() / date.today() を直接参照しない設計（target_date 引数ベースで動作）。
- OpenAI 呼び出しはリトライとフェイルセーフ（API 失敗時はスコア 0.0 または処理スキップ）を組み合わせて安定化。
- DB 書き込みは冪等（idempotent）に行うことを重視（DELETE→INSERT、ON CONFLICT を想定）。
- テスト容易性を考慮し、OpenAI 呼び出し等をモック差し替え可能な内部関数として抽象化。

---

（補足）本 CHANGELOG はソースコードの内容から推定して作成しています。実際のリリースノートとは差異がある可能性があります。