# Changelog

すべての重要な変更はここに記録されます。

このファイルは「Keep a Changelog」の形式に従い、セマンティックバージョニングを前提としています。  
参照: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-15

初期リリース。日本株自動売買システム「KabuSys」のパッケージ骨格を追加しました。

### 追加 (Added)
- パッケージ初期化
  - `src/kabusys/__init__.py` を追加
    - パッケージ説明ドキュメンテーション文字列: "KabuSys - 日本株自動売買システム"
    - バージョン情報: `__version__ = "0.1.0"`
    - 公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- コアサブパッケージ（プレースホルダ）を追加
  - `src/kabusys/data/__init__.py`（データ取得・管理用）
  - `src/kabusys/strategy/__init__.py`（売買戦略定義用）
  - `src/kabusys/execution/__init__.py`（発注・執行管理用）
  - `src/kabusys/monitoring/__init__.py`（監視・ログ・メトリクス用）
- 上記サブパッケージは現時点ではモジュールの骨組み（空の `__init__.py`）として作成されており、今後の実装で各機能を順次追加予定。

### 変更 (Changed)
- なし

### 修正 (Fixed)
- なし

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

今後のリリースでは、各サブパッケージに対する具体的な機能追加（API、データ取得コネクタ、戦略インターフェース、発注ラッパー、監視機能など）を個別に記載します。