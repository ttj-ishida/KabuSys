# CHANGELOG

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

なお、本CHANGELOGは与えられたソースコードからの推測に基づいて作成しています（自動生成された注釈を含む）。実際のリリース履歴と差異がある可能性があります。

## [0.1.0] - 2026-03-31

### 追加（Added）
- 初回公開: kabusys パッケージのベース実装を追加。
  - パッケージメタ情報を定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。パッケージ公開時のエクスポート: data, strategy, execution, monitoring。
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須項目取得用の _require()、Settings クラスを提供し J-Quants / kabuステーション / Slack / DB / 監視 / システム設定など主要設定にアクセスできるプロパティを実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の制約）と便利なブールプロパティ（is_live, is_paper, is_dev）。

- AI モジュール（src/kabusys/ai/*）
  - ニュースセンチメントスコアリング（score_news）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとにセンチメントを算出、ai_scores テーブルへ安全に書き込む処理を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限によるトークン肥大化対策を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ、レスポンスの厳密なバリデーション、無効レスポンス時のフェイルセーフ（スキップ）を実装。
    - ルックアヘッドバイアス回避のため datetime.today() を参照しない設計（target_date 指定方式）。
    - DuckDB の executemany における空リストの制約を考慮した安全な DELETE/INSERT ロジック。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を生成し market_regime テーブルへ冪等書き込み。
    - マクロセンチメントは OpenAI（gpt-4o-mini）で評価。記事が無い場合や API 失敗時は 0.0 を採用するフェイルセーフ実装。
    - API 呼び出しの再試行・エラーハンドリング・レスポンスパースの堅牢化を実装。
  - AI 関連は OpenAI API キーを引数または環境変数（OPENAI_API_KEY）から解決し、未設定時には明示的にエラーを投げる。

- データモジュール（src/kabusys/data/*）
  - ETL パイプライン（pipeline.py / ETLResult）
    - 差分取得、DB 保存、品質チェック（quality モジュール連携）を想定した ETLResult データクラスを提供。
    - 最終取得日のバックフィルやカレンダ先読み設定、品質問題の収集指針を実装。
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを基に営業日判定・前後営業日探索・期間内営業日の取得機能を実装。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末は非営業日）を使用。
    - calendar_update_job により J-Quants からカレンダーを差分取得して冪等保存する処理を実装（バックフィルと健全性チェックを含む）。
  - jquants_client を想定した外部クライアント層と連携する設計になっている（fetch/save を利用）。

- リサーチモジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対ATR、出来高関連）、Value（PER/ROE）等の計算関数を実装。DuckDB SQL を用いて効率的に計算。
    - データ不足時の None 戻り値、営業日・ウィンドウのバッファ設計などを考慮。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク付けユーティリティ、統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで動作する実装方針。

- 研究ユーティリティの再エクスポート（src/kabusys/research/__init__.py）により主要関数をトップレベルで利用可能に。

### 変更（Changed）
- なし（初回リリースのため該当なし）。

### 修正（Fixed）
- なし（初回リリースのため該当なし）。

### 注意点 / 設計上の決定（Notable design decisions）
- ルックアヘッドバイアス防止:
  - AI スコア算出・レジーム判定・ETL 等、全て target_date を明示して処理し、datetime.today()/date.today() を直接参照しない設計にしている。
- フェイルセーフ:
  - OpenAI API や外部 API の失敗時は致命的に停止せず、影響範囲を局所化して継続（macro_sentiment=0.0, スコア未取得はスキップ 等）。
- DuckDB の互換性対応:
  - executemany に空リストを渡せないバージョン（例: 0.10）を想定したガードを実装。
- .env パーサはシェル風の記法（export、クォート、エスケープ、コメント）に対してかなり堅牢に実装されている。

### 既知の制限 / 今後の改善候補
- OpenAI とのやり取りは gpt-4o-mini の JSON Mode を想定しているため、モデル/API 仕様の変更に伴う調整が必要になる可能性がある。
- news_nlp と regime_detector は OpenAI 呼び出しや JSON 解析のエッジケースに対してログは出すが、より詳細なモニタリングやメトリクス収集の追加が望ましい。
- strategy / execution / monitoring モジュールはトップレベルでエクスポートされているが、本CHANGELOG 形成時点での詳細実装や API はソース全体の範囲によって差があり得るため、利用時は個別ドキュメントを参照のこと。

---

このCHANGELOGはソースコードの解析に基づく推測で作成されています。必要であれば、実際のコミット履歴・リリース日時・変更差分に合わせて日付や項目を調整します。