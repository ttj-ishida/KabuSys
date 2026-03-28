# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※日付はコードベースの現在状態に基づき推定しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装・公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定。
  - パブリック API: `kabusys` の主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは `export KEY=val`、クォート、エスケープ、インラインコメントに対応。
  - `Settings` クラスを提供し、必須環境変数の取得・検証を行うプロパティを公開。
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト有）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 実行環境: `KABUSYS_ENV`（development, paper_trading, live の検証）
    - ログレベル検証: `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- ニュース NLP / AI (kabusys.ai)
  - ニュースセンチメントスコアリング機能（news_nlp.score_news）。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
    - raw_news + news_symbols を銘柄単位で集約し、1銘柄あたり最大記事数/文字数でトリム。
    - OpenAI（gpt-4o-mini）へバッチ送信（チャンクサイズ最大 20 銘柄）。
    - JSON Mode（厳密 JSON 出力）を想定し、応答のバリデーション・数値変換・±1.0 でクリップして ai_scores に保存。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API 呼び出しはテスト用に差し替え可能（内部の _call_openai_api を patch）。
  - 市場レジーム判定機能（ai.regime_detector.score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロキーワードによるニュース抽出、LLM スコア化（gpt-4o-mini、JSON Mode）、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実行。
    - レトライや 5xx ハンドリングを含む堅牢な API 呼び出しロジックを実装。

- データ基盤 (kabusys.data)
  - ETL パイプライン基盤（pipeline.ETLResult を含む）。
    - 差分更新、バックフィル、品質チェックの設計を反映した ETLResult データクラスを提供（品質問題やエラーの収集と要約）。
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの差分取得および market_calendar テーブルへの冪等保存ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に未登録の日時がある場合の曜日ベースフォールバック（主に土日除外）。
    - 最大探索日数やバックフィルなどの安全措置を実装。

- リサーチ / ファクター群 (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials からの取得）。
    - DuckDB SQL を主体にし、prices_daily / raw_financials のみ参照する設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns、デフォルト horizons [1,5,21]）。
    - IC 計算（calc_ic: スピアマンランク相関）。
    - ランク化ユーティリティ（rank: 同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - zscore_normalize を含むデータユーティリティを再エクスポート。

### 仕様上の留意点 (Notes)
- ルックアヘッドバイアス防止:
  - AI / ニュース / レジーム / ETL / リサーチの各モジュールは内部で datetime.today() / date.today() を直接参照せず、必ず外部から与えられる target_date を使用するよう設計。
- フェイルセーフ設計:
  - API 呼び出し失敗時は致命エラーとせずフォールバック（例: macro_sentiment=0.0、スコアスキップ）して全体処理を継続する方針。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部の _call_openai_api を patch して差し替え可能にしている（ユニットテストでのモック化を想定）。
- DuckDB 互換考慮:
  - executemany に空リストを渡せない環境（DuckDB 0.10 等）への配慮を行い、空チェックを行っている箇所がある。

### 既知の制限 / 未実装 (Known issues / TODO)
- PBR・配当利回り等の一部バリューファクターは現バージョンで未実装。
- strategy / execution / monitoring の詳細実装はこのリリースでの公開範囲に応じて段階的に追加予定（エクスポートのみ確認）。
- JSON mode を前提とする AI 応答に対して、LLM 側の出力変動（前後テキスト混入など）に対する復元ロジックは実装済みだが、複雑なケースでは手作業の監査が必要になる可能性あり。

### セキュリティ (Security)
- セキュリティ関連の修正・脆弱性情報はこのリリース時点では報告されていません。
- 環境変数に API キーを含むため、運用時は適切なシークレット管理を推奨します（.env ファイルの権限管理等）。

---

(今後のリリースでは各モジュールの改良点・バグ修正・API 互換の変更を個別に記録します。)