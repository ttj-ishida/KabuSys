# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
現在のパッケージバージョン: 0.1.0

フォーマット:
- Added: 新機能
- Changed: 既存機能の重要な変更
- Fixed: バグ修正
- Removed / Deprecated / Security 等は該当があれば記載

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__、__version__ = "0.1.0"）。
  - サブパッケージの公開インターフェースを設定（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索し、CWD に依存しない実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサは次の表現をサポート:
      - コメント行、空行、先頭に `export ` を含む行
      - シングル/ダブルクォート内でのバックスラッシュエスケープ
      - クォートなしの場合のインラインコメント認識（直前がスペース/タブの場合）
    - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能:
    - J-Quants / kabuステーション / LINE / DB（duckdb/sqlite）/ 監視設定 / システム設定等のプロパティを用意。
    - 必須環境変数取得のための _require()（未設定時は ValueError を送出）。
    - KABUSYS_ENV と LOG_LEVEL に対する値検証（正しい列挙値でない場合は ValueError）。
    - 利便性プロパティ: is_live / is_paper / is_dev。

- AI（自然言語処理）関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON Mode で投げてセンチメントを算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を JST→UTC に変換して比較するロジック（calc_news_window）。
    - バッチ処理: 最大 20 銘柄ずつのチャンク送信（_BATCH_SIZE）。
    - 1銘柄ごとの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
    - レスポンスの検証ロジックを実装（JSON パース、results リスト、code/score の存在、未知コード除外、数値性・有限値検査）。
    - スコアは ±1.0 でクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT の形で部分書き換え）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライを実装。その他のエラーはスキップして継続するフェイルセーフ設計。
    - OpenAI クライアント呼び出しはテスト時に差し替え可能（関数を分離）。
    - OpenAI API キーが未設定の場合は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）判定を行う。
    - MA200 比率計算（target_date 未満のデータのみ使用してルックアヘッドを排除）。
    - マクロニュース抽出（タイトルベースでマクロキーワードにマッチする記事を取得）。
    - OpenAI によるマクロセンチメント評価（JSON のみを期待）、API 失敗時は macro_sentiment = 0.0 へフォールバック。
    - レジームスコア合成と閾値判定、結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しのリトライ・エラー処理、レスポンスパース失敗時のフォールバックを実装。
    - OpenAI API キーが未設定の場合は ValueError を送出。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールを提供:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。必要行数不足時は None。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損時は None）と ROE を計算。
    - 設計方針として DuckDB 上で完結し、本番発注API等にアクセスしないことを明記。
  - feature_exploration モジュールを提供:
    - calc_forward_returns: 指定ホライズン（営業日ベース）後のリターンを一括で取得。horizons の検証あり（1..252）。
    - calc_ic: Spearman（ランク）での Information Coefficient を計算。サンプル数不足時は None。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties 判定を安定化）。
    - factor_summary: 各カラムに対する count/mean/std/min/max/median を計算。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定、次/前営業日取得、期間内の営業日列挙、SQ日判定などのユーティリティを実装。
    - DB（market_calendar）にデータがない場合は曜日ベース（土日を祝日扱い）でフォールバック。
    - 最大探索範囲を設定して無限ループを回避（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API（jquants_client）からカレンダー差分を取得し冪等的に保存。バックフィル（直近 _BACKFILL_DAYS）を常に再フェッチし、健全性チェックを実施（不自然に未来日がある場合はスキップ）。
  - ETL / pipeline:
    - ETLResult dataclass を実装して公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュール方針: 差分更新、保存（idempotent）、品質チェック（quality モジュールとの連携）、backfill をサポート。
    - ETLResult は to_dict() を提供し、quality_issues をシリアライズ可能に変換。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、datetime.today() / date.today() を内部ロジックで直接参照しない設計方針が明記されている（API 呼び出しや判定は外部から渡された target_date を使用）。
- OpenAI 呼び出しは JSON Mode を前提にレスポンスを厳密に検証する実装。応答の不整合や API 障害に対してフェイルセーフ（スコア 0.0 で継続、部分的にスキップ）を採用している。
- DuckDB 特性（executemany の空パラメータ制約など）に配慮した実装が行われている（空リストを executemany に渡さない等）。
- 環境変数や API キーが必須の機能（OpenAI, J-Quants, Kabu）では未設定時に明示的に ValueError を投げている。

### Known limitations
- OpenAI API キー（OPENAI_API_KEY）が必須。未設定時は該当関数が ValueError を送出する。
- 実行には duckdb、openai SDK 等の依存がある。
- 一部の外部クライアント（jquants_client 等）は別モジュール（kabusys.data.jquants_client）として想定されており、外部 API の挙動に依存する。

---

今後の更新にあたり、各機能（AI モジュールのプロンプト改善、ETL の部分失敗ハンドリングの拡張、テストカバレッジ強化、ドキュメント追加）を予定しています。