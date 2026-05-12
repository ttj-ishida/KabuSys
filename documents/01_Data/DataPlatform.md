# Data Platform (データ・インフラ基盤)

- 対象: 日本株自動売買基盤における全データパイプライン
- 版数: v1.2 (Bootstrap --local / --truncate / フラット構造対応を追記)

---

## 1. 目的

本ドキュメントは、日本株自動売買システムにおける **データ基盤（Data Platform）** の設計を定義する。

本システムは、精巧な推測・予測（アルゴリズム）の前に、**「完全で一貫性のあるデータ」**が全てを決定する「データ駆動型システム」であり、以下の処理がすべてデータ基盤上で行われる。

- 市場データ収集
- ニュースデータ収集
- 特徴量生成
- AIスコア生成
- 売買シグナル生成
- バックテスト
- 実運用ログ保存

そのため、**安定したデータ取得・保存・管理の仕組み**がシステムの中核となる。

---

## 2. データ基盤の基本思想

本データ基盤は以下の原則で設計する。

1. **全データを履歴として保存する**: 取消されたシグナルやエラーログもAudit Trail（監査証跡）として永続化する。
2. **バックテスト再現性を保証する**: 未来情報（Look-ahead bias）をシステムレベルで遮断する。
3. **データ更新と分析処理を分離する**: Raw/Processedの分離により、抽出時の生データを保持して再処理可能にする。
4. **Idempotency (冪等性)を徹底する**: 何度再実行しても同じ結果（重複排除）となるパイプラインを構築する。
5. **将来のデータ拡張に対応可能な構造にする**

---

## 3. データソース

本システムで使用する主要データソースは以下とする。

### 3.0 情報源の役割分担方針

低コスト最小構成（J-Quants + kabuステーション API + TDnet + EDINET + Yahoo News）における各情報源の役割を以下のように定義する。

| 情報源 | 役割 | 唯一の正 |
| --- | --- | --- |
| **J-Quants** | 市場・財務・銘柄マスタの基盤データ源。日足株価・財務・銘柄一覧・カレンダー・配当・TOPIX はすべて J-Quants から取得する | ✅ 価格・ファンダメンタル・銘柄マスタ系の入力データは J-Quants を唯一の正とする（バックテスト/特徴量/価格系シグナル） |
| **kabuステーション API** | 実運用における執行・口座余力・保有残高・最新値の唯一の正。発注・約定・ポジション現況はこの API のみを参照する | ✅ 本番執行系は他ソースで代替しない |
| **適時開示情報閲覧サービス (TDnet)** | 適時開示イベントの中核情報源。決算短信・業績修正・自己株取得・増資等を全件保存しイベント DB 化する。「先に全件保存して後から参照する」方式を採用。TDnet API は月額コストが高いため当面は閲覧サービスから取得する | ✅ 開示イベントの主情報源（Issue #198） |
| **EDINET API** | TDnet で取得できない法定開示（有報・四半期報告・大量保有等）の補完層。無料 API で取得可能 | ✅ 法定開示の補完（Issue #199） |
| **Yahoo News** | 補助ニュース源。ニュースセンチメント分析の入力として使用するが、売買判断の主役にはしない。シグナルへの影響は AI スコア経由で最大 10% 以内に限定する（`RiskManagement.md` 参照） | ❌ 主役にしない。シグナル生成の決定要因にしない |
| **会社四季報オンライン** | 自動収集基盤ではなく、人手による銘柄調査の補助参照先。システムが自動取得・連携することはしない | ❌ 自動収集しない |

### 3.1 外部データ (API/RSS等)

| データ               | ソース                         | 取得方式                  | 概要                                       |
| -------------------- | ------------------------------ | ------------------------- | ------------------------------------------ |
| 株価（日足）、出来高 | J-Quants                       | 差分 API / Bulk API       | OHLCV・分割調整係数                        |
| 財務データ           | J-Quants                       | 差分 API / Bulk API       | 四半期ごとのBS/PLサマリ                    |
| 銘柄マスタ           | J-Quants                       | 差分 API / Bulk API       | 銘柄一覧・上場情報                         |
| JPXカレンダー        | J-Quants                       | 差分 API / Bulk API       | 祝日、半日取引、SQ日フラグ                 |
| 配当情報             | J-Quants Bulk API              | Bulk API のみ             | 配当率・権利落ち日・支払日等               |
| TOPIX 日足           | J-Quants Bulk API              | Bulk API のみ             | regime_detector の ma200_ratio 算出に使用  |
| 適時開示一覧         | 適時開示情報閲覧サービス (TDnet) | HTTP スクレイピング / XML | 開示イベント全件を `raw_disclosures` に保存（先に全件保存・後から参照）。31日掲載制限あり |
| 法定開示（有報等）   | EDINET API                     | REST API（無料）          | TDnet で取れない有報・四半期報告・大量保有等の補完 |
| ニュース記事（補助） | Yahoo News                     | RSS                       | ニュースセンチメント分析の補助入力。売買判断の主役にはしない |

#### J-Quants API 認証方式

J-Quants API v2 では全エンドポイントで API キー認証を使用する（v1 のリフレッシュトークン／ID トークン方式は廃止）。

| API 種別            | エンドポイント  | 認証ヘッダー       | 設定キー               |
| ------------------- | --------------- | ------------------ | ---------------------- |
| 通常 API (V2)       | `/v2/*`         | `x-api-key: {key}` | `JQUANTS_BULK_API_KEY` |
| Bulk Download API   | `/v2/bulk/*`    | `x-api-key: {key}` | `JQUANTS_BULK_API_KEY` |

> ⚠️ Bulk Download API の利用には **Standard プラン以上**が必要。Free/Light プランでは `/bulk/list` が HTTP 403 を返す。

### 3.2 内部生成データ (自システム)

| データ             | ソース               | 概要                                                    |
| ------------------ | -------------------- | ------------------------------------------------------- |
| 取引履歴・口座情報 | kabuステーション API | 発注要求、WebSocketからのPUSH約定データ、ポジション現況。実運用の執行系における唯一の正 |
| AI推論結果         | AI Engine            | NLPスコア、レジーム判定                                 |
| シグナル・特徴量   | Strategy/Research層  | モメンタム等の因子、最終シグナル                        |

---

## 4. データレイヤー構造とETLパイプライン

データは以下の3層構造で管理され、ETLパイプラインを通じて更新される。

```
Data Fetch -> [ Raw Layer ] -> Data Cleaning -> [ Processed Layer ] -> Feature Gen -> [ Feature Layer ]
```

### 4.1 ETL方針と制約

- **Idempotency (冪等性)**: データ取得・変換ジョブは一意制約（Unique constraints）により、重複して登録されないように設計する。
- **差分更新とAPIスロットリング**: J-Quants APIの利用上限（120リクエスト/分）等を超えないようにスロットル制御（Rate-limiting）を設け、効率よく差分のみを取得する。

### 4.2 主要ジョブ（日次差分更新）

日次差分更新で使用する J-Quants エンドポイントと制約：

| ETL ジョブ | エンドポイント | 備考 |
| --- | --- | --- |
| `run_prices_etl()` | `/equities/bars/daily` | `date` or `code` 必須。全銘柄時は `date=YYYY-MM-DD` で1日ずつ取得 |
| `run_financials_etl()` | `/fins/summary` | 同上。Bulk と同一エンドポイント |
| `run_dividends_etl()` | `/fins/dividend` | Standard プランでは HTTP 403。Premium 以上が必要 |
| `run_topix_etl()` | `/indices/bars/daily/topix` | 当日分取得済みの場合はスキップ |
| `calendar_update_job` | `/markets/calendar` | 祝日・SQ日など |

- `calendar_update_job`: J-Quants等からJPXカレンダー情報（祝日・SQ日など）を取得し、`market_calendar` テーブルを更新する夜間バッチ処理。
- `run_topix_etl()`: J-Quants `/indices/bars/daily/topix` エンドポイントから TOPIX 日足（OHLC）を差分取得し、`topix_daily` テーブルへ UPSERT する。`run_daily_etl()` の Step 5 として実行される（Issue #257）。当日分取得済みの場合はバックフィルも含めてスキップ。TOPIX は JPX 公式指数のため過去日付の訂正配信はほぼ発生しない。

### 4.3 Bootstrap フロー（初回一括投入）

通常の差分更新では非効率な初回環境構築時に、**J-Quants Bulk Download API** を使って大量のヒストリカルデータを一括投入する。

```
J-Quants Bulk API
  GET /v2/bulk/list?endpoint=<ep>  → ファイルキー一覧
  GET /v2/bulk/get?key=<key>       → presigned URL（有効期限5分）
      ↓ gzip CSV ダウンロード
  data/bootstrap/raw/<endpoint>/   ← サブディレクトリ構造（runner がダウンロードした形式）
  data/bootstrap/raw/              ← フラット構造も対応（手動配置・一括 DL 形式）
                                     例: equities_bars_daily_202401.csv.gz
      ↓ parse & schema validation
  raw_prices / raw_financials / stocks / market_calendar / topix_daily
      ↓ ETL（NOT NULL / 型検証 → ON CONFLICT DO UPDATE）
  prices_daily / fundamentals
      ↓ 処理結果記録
  bootstrap_load_history           ← ファイル単位の処理状態管理
```

#### ファイル配置形式

Bootstrap は以下2つのファイル配置形式に対応する。両方が存在する場合はファイル名で重複排除し、サブディレクトリ側を優先する。

| 形式 | パス例 | 説明 |
| ---- | ------ | ---- |
| サブディレクトリ | `raw/equities/bars/daily/202401.csv.gz` | runner が自動ダウンロードする形式 |
| フラット | `raw/equities_bars_daily_202401.csv.gz` | 手動配置・外部ツールでの一括 DL 形式 |

> **重複日付の扱い**: 月次ファイルと日次ファイルが同じ日付のデータを含む場合でも `ON CONFLICT DO UPDATE` により DB 上の重複行は発生しない。後からロードされたデータが上書きされる。

#### 取り込み対象エンドポイント（Standard プラン）

| Bulk エンドポイント            | 保存先（Raw）     | 保存先（Processed）   | 備考                       |
| ------------------------------ | ----------------- | --------------------- | -------------------------- |
| `/equities/bars/daily`         | `raw_prices`      | `prices_daily`        | AdjFactor を raw に保存    |
| `/equities/master`             | —                 | `stocks`              | 最新日のみ取得             |
| `/fins/summary`                | `raw_financials`  | `fundamentals`        | 既存スキーマに対応         |
| `/markets/calendar`            | —                 | `market_calendar`     | 既存スキーマに対応         |
| `/indices/bars/daily/topix`    | —                 | `topix_daily`         | regime_detector が参照     |

> ⚠️ `/fins/dividend` は **Standard プランでも HTTP 403**（Premium プラン以上が必要）。Bootstrap 対象外であり、`run_dividends_etl()` もスキップされる。配当データは初回 Bootstrap CSV 投入分のみ利用可能。

#### 冪等性・エラー方針

- `bootstrap_load_history` にファイル単位で `pending / loaded / failed` を記録
- 再実行時は `loaded` 済みファイルをスキップ
- 1ファイル失敗でも他ファイルは継続し、エラーをログ記録
- DuckDB への挿入は `ON CONFLICT DO UPDATE` で常に冪等

#### CLI

```bash
# 続きから実行（デフォルト。bootstrap_load_history でロード済みファイルをスキップ）
python -m kabusys.data.bootstrap

# ドライラン（ダウンロードせず件数確認のみ）
python -m kabusys.data.bootstrap --dry-run

# 特定エンドポイントのみ処理
python -m kabusys.data.bootstrap --endpoint /equities/bars/daily

# 初期化して最初から実行（履歴 + キャッシュを全削除、確認プロンプトあり）
python -m kabusys.data.bootstrap --fresh
python -m kabusys.data.bootstrap --fresh --yes   # 確認スキップ

# ローカルファイルのみ処理（API を呼ばずオフライン投入）
# raw_dir 内の .gz ファイルをサブディレクトリ・フラット両構造で検索して処理する
python -m kabusys.data.bootstrap --local
python -m kabusys.data.bootstrap --local --raw-dir /path/to/gz/files

# データテーブルを全削除してからインポート（raw_dir のファイルは保持）
# bootstrap_load_history 以外の全データテーブルを DELETE して最初から投入し直す
python -m kabusys.data.bootstrap --truncate --yes

# 詳細ログ出力
python -m kabusys.data.bootstrap --verbose
```

処理の進捗はリアルタイムで標準出力に表示される（ファイル単位のダウンロード/ロード状況）。

### 4.4 適時開示収集パイプライン（Issue #198 / #199）

適時開示は「対象銘柄になってから取得する」方式ではなく、**「先に全件保存して後から参照する」** 方式を採用する。これにより、ポートフォリオ外の銘柄が将来ユニバースに加わった際もイベント履歴を遡参照できる。

```
TDnet 適時開示閲覧サービス（15:35 ジョブ）
  → 当日開示一覧を全件取得（開示日時 / 銘柄コード / 表題 / URL）
  → raw_disclosures（ON CONFLICT IGNORE で冪等保存）
      ↓
EDINET API（15:40 ジョブ、法定開示補完）
  → 有報 / 四半期報告 / 大量保有等を補完
  → raw_disclosures（source='edinet'）
      ↓
開示分類ジョブ（17:00）
  → 表題ベースの分類ルール（event_type）を適用
  → event_score / buy_caution フラグを付与
  → disclosure_events
```

**冪等性**: `raw_disclosures` の主キーは開示 ID（TDnet: 開示番号 / EDINET: docID）。重複取得しても `ON CONFLICT DO NOTHING` で安全。

**EDINET API v2 実装メモ**: 書類種別コードは `docTypeCode` フィールド（`docType` ではない）。銘柄コードは `secCode`（5桁: JPX 4桁 + "0"）で返るが、現実装では `code=NULL` にマップ。認証は `Subscription-Key` クエリパラメータ。

**31日掲載制限への対策（TDnet）**: TDnet 閲覧サービスには掲載期限（約31日）がある。毎日の差分取得で取りこぼしを防ぐ。取得漏れは `raw_disclosures` の日付ギャップ検出で検知する。

---

## 5. Raw Layer（生データ）

外部ソースから取得したデータをそのまま保存する。

- **目的**: パースエラー時の再処理担保、元データの保持
- **主なテーブル**: `raw_prices`（`adj_factor` 列含む）, `raw_financials`, `raw_news`, `raw_executions`
- **Bootstrap キャッシュ**: `data/bootstrap/raw/<endpoint>/` に gzip CSV を保存（再ダウンロード防止）

---

## 6. Processed Layer（整形データ）

Rawデータを分析可能な形式に整形する。

- **処理内容**: 欠損補完、重複除去、日付整形、銘柄コード統一
- **主なテーブル**: `prices_daily`, `financials_clean`, `news_clean`

### 6.1 基礎データの補正ルール（極めて重要）

本番環境とバックテスト環境の乖離を生じさせないため、データプラットフォーム側で以下の厳密な管理を行う。

1. **財務データの発生日 (Look-ahead防止)**:
   - 財務発表日（開示日）を基準に「いつからシステムがそのデータを知り得たか」をフラグ・時刻管理する。
   - **15時以降（大引け後）の発表は、システム上『翌営業日』のデータとして扱う**。
2. **価格の調整（分割・併合）**:
   - 株式分割等が実施された場合、過去の株価情報に対して「調整済み価格 (Adjusted Price)」を再計算して一元提供する。
   - 分析時に `調整前` と `調整後` が混在しないビューを強制する。

---

## 7. Feature Layer（特徴量）とAIレイヤー

分析やAIモデルで利用する特徴領域。

- **主なテーブル**: `feature_snapshot` (モメンタム、バリュー等)、`ai_scores` (ニュースセンチメント、マクロスコア、確信度)、`market_regime`

---

## 8. データベース構成とトレーサビリティ設計

**推奨データベース:** `PostgreSQL` または `DuckDB + Parquet`（時系列および分析処理に特化）

### 8.1 冪等・トレーサビリティ（Audit Trail）の設計

システム上で「シグナル」から「約定」に至るフローを完全にトレースするため、全テーブルを以下の階層をもつ一貫したキー（`uuid`等の識別子）で連結する。

```text
business_date (営業日)
  └─ strategy_id (戦略バージョン)
       └─ signal_id (シグナル固有ID)
            └─ order_request_id (内部発注ID / 冪等キー)
                 └─ broker_order_id (証券会社受付ID)
```

**監査ログの徹底**: エラーで行われなかった発注や、リスク管理（3段階ガード）によって棄却されたシグナルも、単に破棄するのではなくステータス（例: `REJECTED_BY_RISK`）を付与して必ず永続化する。

### 8.2 主なテーブル構成（論理例）

- `stocks`: 銘柄コード、銘柄名、セクター
- `prices_daily`: date, code, open, high, low, close, volume, adjusted_close
- `financials_clean`: 四半期財務データ指標（EPS, PBRベース等）
- `raw_news`: id, datetime, source, title, content, url, fetched_at
- `ai_scores`: date, code, news_score, macro_score, confidence
- `signal_events`: signal_id, date, code, final_score, decision (Buy/Sell/Hold)
- `order_requests`: order_request_id, signal_id, status, requested_qty
- `executions`: execution_id, order_request_id, filled_qty, fill_price, commission

---

## 9. データ品質管理と保存方針

### 9.1 品質管理 (Data Quality)

- **チェック項目**: 欠損データ、重複データ、異常値（スパイク等）、日付不整合
- **異常検知時のアクション**: 即時ETL停止（Fail-Fast）および警告ログ出力（LINE等へのアラート）。

### 9.2 保存ポリシー

- **保存対象**: 上記に定義される全データ（Raw, Processed, Feature, 監査ログ）
- **保存期間**: 永続保存（バックテスト再現性と監査性の確保のため）

---

## 10. パフォーマンス最適化

- **フォーマット**: DuckDBの利用時は、Parquet保存によるカラムナストレージ化。
- **インデックスとパーティション**: 大規模な時系列テーブル（例: `prices_daily`）は、日付 (`date`) によるパーティション分割を行いスキャン速度を最適化する。

---

## 11. まとめ

データ基盤は以下のシームレスなパイプラインを担う。

```
データ取得/保存 -> ETL/スロットリング制限 -> 特徴量・スコア生成 -> AI分析 -> 戦略計算(シグナル) -> 執行・履歴保存
```

単なるデータストアにとどまらず、UUIDの連鎖による追跡可能性と、ルックアヘッドを防ぐ厳格な補正ルールにより、バックテストと本番運用の双方で**「齟齬のない最強の分析・執行基盤」**を実現する。
