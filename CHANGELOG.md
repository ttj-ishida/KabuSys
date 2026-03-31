# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
タグ付けは SemVer（MAJOR.MINOR.PATCH）に従います。

## Unreleased

（現時点で未リリースの変更はありません）

---

## 0.1.0 - 2026-03-31

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主要な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージ定義（__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。

- 設定管理
  - 環境変数 / .env 読み込みユーティリティを実装（kabusys.config）。
  - プロジェクトルート検出（.git / pyproject.toml）に基づく自動 .env ロード機能。
  - .env/.env.local の優先度制御、OS 環境変数保護（protected set）対応。
  - export 形式やクォート・コメントの取り扱いなど、堅牢な .env パーサー実装。
  - Settings クラスで各種必須/任意設定をプロパティ化（J-Quants、kabu API、Slack、DB パス、環境種別・ログレベル検証など）。

- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄単位で OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを生成。
    - バッチ処理（銘柄ごとに最大 _BATCH_SIZE=20）・記事数/文字数制限・トリム処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code/score 検証、数値正規化、±1.0 クリップ）。
    - テスト容易性を考慮し、OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。
    - ai_scores テーブルへの冪等書き込み（対象コードの DELETE → INSERT）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - prices_daily / raw_news を参照し、OpenAI を用いた macro_sentiment 評価（記事がない場合は LLM 呼び出しをスキップし 0.0 を使用）。
    - API エラーに対するリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため、すべての関数は target_date 引数を使用（date.today() を参照しない設計）。

- データプラットフォーム（DuckDB ベース）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定・前後営業日取得・範囲内営業日取得・SQ 日判定の実装。
    - market_calendar が未取得時は曜日（週末）ベースでフォールバックする一貫した振る舞い。
    - JPX カレンダー夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェック・冪等保存を実施。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - 差分更新ロジック、backfill、IDempotent 保存（jquants_client の save_* を使用）・品質チェック呼び出し（quality モジュール）を含む ETLResult データクラスを提供。
    - ETL 実行結果を集約する ETLResult（target_date, fetched/saved カウント、quality_issues, errors, helper プロパティ/辞書化）を実装。
    - DuckDB におけるテーブル存在チェック・最大日付取得ユーティリティを提供。

  - jquants_client 連携ポイントを想定（fetch / save の呼び出し場所を用意）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高関連）、Value（PER, ROE）を DuckDB SQL で実装。
    - データ不足時の None 扱い、営業日ベースのホライズン設計、効率的なスキャン窓（バッファ）を採用。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン, デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）。
    - Pandas 等に依存しない純標準ライブラリ実装。

- 開発・運用面の配慮
  - ロギングと詳細な警告メッセージを各モジュールに実装（診断しやすい）。
  - テスト容易性のため外部 API 呼び出しの差し替え（モック化）を明示的に想定。
  - 外部依存を最小化（例：リサーチは標準ライブラリ + DuckDB のみを利用）し、運用時の安定性を重視。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト環境向け）。
- .env の読み込み時に OS 環境変数を保護するロジック（protected set）を実装。

### Notes / Implementation Decisions
- ルックアヘッドバイアス対策として、すべての「日付を基準とする処理」は target_date を引数にとり、内部で date.today() や datetime.today() を参照しない設計を採用。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を期待する実装。ただし外部 SDK のバージョン差異（APIError のステータスコード有無など）に対しても堅牢に動作するようエラーハンドリングを行っている。
- DuckDB 固有の挙動（executemany に空リストを渡せない等）への互換性対策を実装。
- データ欠損や API エラー時は処理を継続するフォールバック（ゼロスコアやスキップ）を採用し、部分失敗が全体を停止させないようにしている。

---

今後の予定（例）
- strategy / execution / monitoring パッケージの具体的な発注ロジック・実行エンジンの実装。
- ユニットテスト・統合テストの追加、CI 設定。
- 性能改善（大規模データ向けクエリ最適化）や運用向けメトリクス出力。

（以上）